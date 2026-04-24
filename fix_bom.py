import os

files_to_fix = [
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_airtable.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_scraper.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_booking_scraper.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\headout_continuous_run.py",
    r"c:\Users\Aloosh2020\Downloads\New Project's\HeadoutSystem\requirements.txt",
]

for file_path in files_to_fix:
    if os.path.exists(file_path):
        # Read with utf-8-sig to automatically handle BOMs
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content_str = f.read()
            
        # Clean any remaining ZERO WIDTH NO-BREAK SPACE characters
        content_str = content_str.lstrip('\ufeff')
        
        # Write back as clean utf-8
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content_str)
            
        print(f"Processed: {file_path}")
