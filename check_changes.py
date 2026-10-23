import sqlite3
from pathlib import Path
from change_detection import save_report


def main():
    report,path = save_report(Path(__file__).resolve().parent)
    print('Comparing the latest two successful captures per webpage.')
    for page in report['pages']:
        print(f"{page['brand']} | {page['status']} | {page['source_url']}")
    batch=report.get('latest_batch')
    if batch:
        print('Failures in latest batch:',len(batch.get('failed_pages',[])))
        if batch.get('error'):
            print('Could not read latest batch report:',batch['error'])
    print('Change report:',path)
    print('No registry records or operating statuses were changed.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as error:
        print('Could not compare:',error)
        raise SystemExit(1)
