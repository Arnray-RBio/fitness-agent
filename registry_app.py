"""Create permanent locations by explicitly linking capture candidates."""
import copy
import json
import sqlite3
from pathlib import Path

import streamlit as st
from overview_app import group_captures, load_data
from registry_store import (CATEGORIES, STATUSES, connect, create_branch, get_branches,
                            get_brands, get_links, initialize, link_existing, update_branch)

DATABASE_PATH = Path(__file__).resolve().parent / 'data' / 'fitness_agent.db'


def branch_fields(initial, prefix):
    details = copy.deepcopy(initial)
    details['name'] = st.text_input('Branch name', initial.get('name') or '', key=prefix+'_name').strip()
    details['name_evidence'] = st.text_area('Evidence identifying the branch',
        initial.get('name_evidence') or initial.get('evidence') or '', key=prefix+'_name_evidence').strip()
    details['address'] = st.text_input('Full address, including unit (blank if unknown)',
        initial.get('address') or '', key=prefix+'_address').strip() or None
    details['address_evidence'] = st.text_area('Address evidence', initial.get('address_evidence') or '',
        key=prefix+'_address_evidence').strip()
    if not details['address']:
        details['address_evidence'] = ''
    details['categories'] = st.multiselect('Categories confirmed at this branch', CATEGORIES,
        default=[c for c in initial.get('categories', []) if c in CATEGORIES], key=prefix+'_categories')
    details['category_evidence'] = st.text_area('Evidence for the branch categories',
        initial.get('category_evidence') or '', key=prefix+'_category_evidence').strip()
    status = initial.get('operating_status', 'unknown')
    details['operating_status'] = st.selectbox('Operating status',STATUSES,
        index=STATUSES.index(status) if status in STATUSES else 0,key=prefix+'_status')
    details['status_evidence'] = st.text_area('Evidence supporting operating status',
        initial.get('status_evidence') or '',key=prefix+'_status_evidence').strip()
    details['verification_source_url'] = st.text_input('Verification source URL',
        initial.get('verification_source_url') or '',key=prefix+'_url').strip()
    details['verified_on'] = st.text_input('Verification date (YYYY-MM-DD)',
        initial.get('verified_on') or '',key=prefix+'_date').strip() or None
    details['review_notes'] = st.text_area('Branch notes', initial.get('review_notes') or '',key=prefix+'_notes')
    return details


def main():
    st.set_page_config(page_title='Permanent branch register',layout='wide')
    st.title('Permanent branch register')
    st.caption('Explicitly link observations to physical locations. New captures never overwrite register details automatically.')
    if not DATABASE_PATH.exists():
        st.error('Database not found. Run your importer first.')
        st.stop()
    try:
        initialize(DATABASE_PATH)
        rows,reviews = load_data()
        branches = get_branches(DATABASE_PATH)
        brands = get_brands(DATABASE_PATH)
        links = get_links(DATABASE_PATH)
    except (sqlite3.Error,ValueError,KeyError) as error:
        st.error(f'Could not load register: {error}')
        st.stop()
    message=st.session_state.pop('registry_success',None)
    if message:
        st.success(message)
    first,second,third=st.columns(3)
    first.metric('Registered brands',len(brands))
    second.metric('Permanent branch records',len(branches))
    third.metric('Recorded as operating',sum(b['details']['operating_status']=='operating' for b in branches))
    st.info('These totals cover your register only. They are not Singapore-wide totals. Verification can become outdated; review its date.')
    register_tab,link_tab=st.tabs(['Branch register','Link capture candidates'])
    with register_tab:
        if not branches:
            st.write('The register is empty. Open Link capture candidates to create the first location.')
        else:
            st.dataframe([{'Branch ID':b['id'],'Brand':b['brand_name'],'Branch':b['name'],
                'Address':b['details'].get('address'),'Categories':', '.join(b['details'].get('categories',[])),
                'Status':b['details']['operating_status'],'Verified on':b['details'].get('verified_on'),
                'Linked observations':b['observations']} for b in branches],width='stretch',hide_index=True)
            st.caption('Category totals may overlap because one branch can offer multiple types of service.')
            totals=[{'Category':c,'Registered branches':sum(c in b['details'].get('categories',[]) for b in branches),
                'Recorded as operating':sum(c in b['details'].get('categories',[]) and b['details']['operating_status']=='operating' for b in branches)} for c in CATEGORIES]
            st.dataframe(totals,width='stretch',hide_index=True)
            branch_by_id={b['id']:b for b in branches}
            branch_id=st.selectbox('Edit a permanent branch',list(branch_by_id),
                format_func=lambda i:f"{i} | {branch_by_id[i]['brand_name']} | {branch_by_id[i]['name']}")
            branch=branch_by_id[branch_id]
            with st.form(f"edit_{branch_id}_{branch['revision']}"):
                details=branch_fields(branch['details'],f"edit_{branch_id}_{branch['revision']}")
                submitted=st.form_submit_button('Save permanent branch details')
            if submitted:
                try:
                    update_branch(DATABASE_PATH,branch_id,branch['revision'],details)
                    st.session_state['registry_success']='Branch updated. Earlier revisions preserved.'
                    st.rerun()
                except (ValueError,sqlite3.Error) as error:
                    st.error(f'Not saved: {error}')
            with st.expander('Linked capture observations'):
                for link in links:
                    if link['branch_id']==branch_id:
                        st.caption(f"Capture {link['capture_id']} | review version {link['review_version']} | linked {link['linked_at_utc']}")
                        st.json(json.loads(link['snapshot_json']))
            with st.expander('Permanent branch revision history'):
                with connect(DATABASE_PATH) as db:
                    for revision in db.execute('SELECT * FROM registry_revisions WHERE branch_id=? ORDER BY revision DESC',(branch_id,)):
                        st.caption(f"Revision {revision['revision']} | {revision['saved_at_utc']}")
                        st.json(json.loads(revision['details_json']))
    with link_tab:
        show_all=st.checkbox('Include historical captures',value=False)
        if show_all:
            selected_rows=sorted(rows,key=lambda r:r['id'],reverse=True)
        else:
            selected_rows=[history[0] for history in group_captures(rows).values()]
        candidates=[]
        for row in selected_rows:
            review=reviews.get(row['id'])
            # A rejected capture review cannot supply candidates for registration.
            if review and review['status']=='rejected':
                continue
            venue=json.loads(review['corrected_venue_json']) if review else json.loads(row['extraction_json'])['venue']
            for index,snapshot in enumerate(venue.get('branches',[])):
                candidates.append(dict(capture_id=row['id'],review_version=review['id'] if review else 0,
                    branch_index=index,snapshot=snapshot,brand=venue.get('name') or row['brand_name'] or '',
                    source_url=row['source_url'],webpage_text=row['webpage_text']))
        if not candidates:
            st.write('No branch candidates in the selected captures. Capture/review branch information first.')
        else:
            chosen=st.selectbox('Choose a captured branch candidate',range(len(candidates)),
                format_func=lambda i:f"Capture {candidates[i]['capture_id']} | {candidates[i]['brand']} | {candidates[i]['snapshot'].get('name','Unnamed')}")
            candidate=candidates[chosen]
            token=f"candidate_{candidate['capture_id']}_{candidate['review_version']}_{candidate['branch_index']}"
            st.write('Source:',candidate['source_url'])
            st.json(candidate['snapshot'])
            with st.expander('Saved source text to check evidence'):
                st.text_area('Source text',candidate['webpage_text'],height=350,disabled=True,key=token+'_text')
            already=next((l for l in links if l['capture_id']==candidate['capture_id'] and l['review_version']==candidate['review_version'] and l['branch_index']==candidate['branch_index']),None)
            if already:
                st.success(f"This observation is already linked to permanent Branch {already['branch_id']}. Edit it in Branch register.")
            else:
                action=st.radio('How should this observation be registered?',
                    ['Link to an existing branch','Create a new branch'],index=0 if branches else 1,key=token+'_action')
                if action=='Link to an existing branch':
                    if not branches:
                        st.write('No permanent branches yet. Choose Create a new branch.')
                    else:
                        branch_by_id={b['id']:b for b in branches}
                        with st.form(token+'_link'):
                            target=st.selectbox('Existing branch',list(branch_by_id),format_func=lambda i:f"{i} | {branch_by_id[i]['brand_name']} | {branch_by_id[i]['name']}")
                            st.caption('Linking records the observation. It does not replace the permanent address, categories or operating status.')
                            confirmed=st.checkbox('I checked that this observation refers to this same physical branch.')
                            submit=st.form_submit_button('Link observation')
                        if submit:
                            try:
                                if not confirmed:
                                    raise ValueError('Check the physical-branch confirmation first.')
                                link_existing(DATABASE_PATH,target,candidate)
                                st.session_state['registry_success']='Observation linked. Permanent details preserved.'
                                st.rerun()
                            except (ValueError,sqlite3.Error) as error:
                                st.error(f'Not linked: {error}')
                else:
                    brand_by_id={b['id']:b for b in brands}
                    brand_choice=st.selectbox('Brand for this new branch',[0]+list(brand_by_id),
                        format_func=lambda i:'Create/reuse brand by name' if i==0 else brand_by_id[i]['name'],key=token+'_brand_choice')
                    initial=copy.deepcopy(candidate['snapshot'])
                    # Explicit verification in this register is required; never inherit operating claims.
                    initial.update(operating_status='unknown',categories=[],category_evidence='',status_evidence='',verified_on=None,
                                   verification_source_url=candidate['source_url'])
                    with st.form(token+'_create'):
                        if brand_choice==0:
                            brand_name=st.text_input('Brand name',candidate['brand'],key=token+'_brand_name')
                        else:
                            brand_name=brand_by_id[brand_choice]['name']
                            st.write('Brand:',brand_name)
                        details=branch_fields(initial,token+'_new')
                        confirmed=st.checkbox('I checked existing branches and this is a distinct physical location.',key=token+'_distinct')
                        submit=st.form_submit_button('Create permanent branch and link observation')
                    if submit:
                        try:
                            if not confirmed:
                                raise ValueError('Check the distinct-location confirmation first.')
                            identifier=create_branch(DATABASE_PATH,brand_name,details,candidate)
                            st.session_state['registry_success']=f'Permanent Branch {identifier} created and observation linked.'
                            st.rerun()
                        except (ValueError,sqlite3.Error) as error:
                            st.error(f'Not created: {error}')


if __name__=='__main__':
    main()
