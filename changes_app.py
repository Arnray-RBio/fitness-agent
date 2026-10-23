from pathlib import Path
import streamlit as st
from change_detection import build_report,save_report

PROJECT_DIR=Path(__file__).resolve().parent
LABELS={
    'baseline_only':'First capture — no comparison',
    'no_detected_change':'No detected change',
    'source_changed_needs_review':'Webpage text changed — review required',
    'extraction_variation_on_unchanged_text':'Model extraction changed on unchanged text',
}


def main():
    st.set_page_config(page_title='Webpage change review',layout='wide')
    st.title('Webpage change review')
    st.caption('Compares original extractions and source text from the latest two successful captures per webpage.')
    try:
        report=build_report(PROJECT_DIR)
    except Exception as error:
        st.error(f'Could not load comparisons: {error}')
        st.stop()
    st.info('A missing extracted branch is not proof of closure. A changed price may be a model error. Check the source before changing the permanent register.')
    if st.button('Save this comparison report'):
        _,path=save_report(PROJECT_DIR)
        st.success(f'Saved: {path.name}')
    batch=report.get('latest_batch')
    if batch:
        with st.expander('Latest collection run: failures and import status',expanded=bool(batch.get('failed_pages') or batch.get('error'))):
            st.json(batch)
            st.caption('Comparisons use successful stored captures. A failed page has no new snapshot and must not be treated as unchanged or closed.')
    pages=report['pages']
    if not pages:
        st.write('No captures available.')
        st.stop()
    st.dataframe([{'Brand':p['brand'],'Page':p['page_type'],'Result':LABELS[p['status']],
        'Latest capture':p['latest_capture_id'],'Previous capture':p.get('previous_capture_id'),
        'Latest checked (UTC)':p['latest_checked_at_utc'],'URL':p['source_url']} for p in pages],width='stretch',hide_index=True)
    selected=st.selectbox('Choose a webpage',range(len(pages)),format_func=lambda i:f"{pages[i]['brand']} | {pages[i]['source_url']}")
    page=pages[selected]
    st.subheader(LABELS[page['status']])
    st.write('Source:',page['source_url'])
    st.caption(f"Latest capture {page['latest_capture_id']} checked {page['latest_checked_at_utc']}")
    for warning in page.get('warnings',[]):
        st.warning(warning)
    if page['status']=='extraction_variation_on_unchanged_text':
        st.write('The source text is unchanged after whitespace normalization. These extraction differences alone do not establish a business change.')
    if page.get('field_changes'):
        st.subheader('Differences in extracted facts')
        st.caption('Newly extracted/no longer extracted describe model output, not confirmed additions or removals. Order, duplicates and evidence wording are ignored.')
        for field,changes in page['field_changes'].items():
            with st.expander(field.capitalize(),expanded=True):
                st.json(changes)
    elif page['status']=='source_changed_needs_review':
        st.write('The page text changed, but no differences were detected in the selected extracted fields.')
    if page.get('source_diff_excerpt'):
        st.subheader('Source text differences')
        st.code(page['source_diff_excerpt'],language='diff')
        if page['source_diff_truncated']:
            st.caption('Showing the first 160 diff lines. Inspect full saved text in the overview for the complete source.')
    st.caption('Review capture evidence in overview_app.py or review_app.py. Make verified location edits in registry_app.py.')


if __name__=='__main__':
    main()
