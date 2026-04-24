import os

files_to_fix = [
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_airtable.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_scraper.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_booking_scraper.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_continuous_run.py",
]

for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Remove BOM if it exists
        if content.startswith(b'\xef\xbb\xbf'):
            with open(file_path, 'wb') as f:
                f.write(content[3:])
            print(f"Removed BOM from: {file_path}")
        else:
            print(f"No BOM found in: {file_path}")
