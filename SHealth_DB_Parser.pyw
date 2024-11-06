# Samsung Secure Health Data Parser
# Author: David Haddad
company = 'Breakpointforensics.com'
script_version = 1.0

'''
Requirements:
    Python 3.11 or greater
Dependencies:
    pandas
    pyautogui
    freesimplegui
    FreeSimpleGUI
    openpyxl
    jinja2
'''

import sqlite3
from datetime import datetime, timezone, date
import pandas as pd
import argparse
import os
from pathlib import Path
from jinja2 import Template
import gzip
import json
import FreeSimpleGUI as sg
import pyautogui
import logging
from ctypes import windll
from sHealth_Type_Map import exercise_count_type_map, exercise_type_map

def check_or_create_folder(folder_path):
    """
    Check if the given folder exists. If not, create it.

    Parameters:
    folder_path (str): The path of the folder to check or create.

    Returns:
    str: The path of the folder.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Existing Log Folder Detected: {folder_path}")
    
    return folder_path

##Get Home dir for user and build paths for setting and log locations
home_dir = Path.home()
appdatalog = (str(home_dir) + '\\AppData\\Local\\BreakpointForensics\\SHealthParser\\Logs\\')
check_or_create_folder(appdatalog)


# Setup logging
today = date.today()
logging.basicConfig(filename=appdatalog + '\\' + str(today) + '_SHealthParser.log',level=logging.DEBUG, force=True, format='%(asctime)s %(message)s')
clear = lambda: os.system('cls')
clear()

#Imports the splash screen controler used only after commpiling with pyinstaller using splashscreen flag.  uses try method in ase pyi_splash not available so program doesn't crash.
try:
    
    import pyi_splash
    
    # Update the text on the splash screen
    pyi_splash.update_text("Loading")
    pyi_splash.update_text("Please be patient...")
    
    # Close the splash screen. It does not matter when the call
    # to this function is made, the splash screen remains open until
    # this function is called or the Python program is terminated.
    pyi_splash.close()
 
except ImportError:
     pass
 

# HTML template with DataTables.js for dynamic sorting/filtering
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        table {
            width: 100%;
            margin: 20px 0;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            border: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
    </style>
</head>
<body>
    <h1>{{reporttype}}</h1>
    <h2>Report generated: {{timestamp}} UTC</h2>
    <table id="data-table" class="display">
        <thead>
            <tr>
            {% for col in columns %}
                <th>{{ col }}</th>
            {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for row in data %}
            <tr>
                {% for item in row %}
                <td>{{ item }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <script>
        $(document).ready(function() {
            $('#data-table').DataTable({
                "pageLength": 100,  
                "lengthMenu": [[50, 100, 250, 500, -1], [50, 100, 250, 500, "All"]]
            });
        });
    </script>
    <footer>
        <p>Script Version: {{ script_version }}</p>
        <p>{{ company }}</p>
    </footer>
</body>
</html>
"""

def process_ringleader(db_path, output_path):
    """Intermediate process before ringleader to handle exception event calls to GUI"""
    
    result = ringleader(db_path, output_path)
    if result == '-END KEY-':
        window.write_event_value('-END KEY-', None)
    elif result == '-ERROR-':
        window.write_event_value('-ERROR-', None)

def ringleader(db_path, output_path):
    try:
        """Orchastrates the various export functions and their calls"""
        logging.info('Calling main ringleader')
        logging.info('Calling step_data parser')
        function_complete = False
        function_complete = export_step_data(db_path, output_path)
        logging.info(f'export_step_data function returned {function_complete}')
        function_complete = False
        function_complete = export_exercise_data(db_path, output_path)
        logging.info(f'export_exercise_data function returned {function_complete}')
        function_complete = False
        live_data_df  = fetch_compressed_live_data(db_path)
        if live_data_df is not None:
            logging.info(f'fetch_compressed_live_data function returned True')
            save_live_data_to_excel(live_data_df, output_path)
        return ('-END KEY-')
    
    except Exception as e:
        logging.error(f"Unexpected error in ringleader: {e}")
        if GUI:
            window['-STATUS-'].update(f"An unexpected error occurred: {e}")
            if "database is locked" in str(e):
                window['-STATUS-'].update(f"Error: Database is Locked")
            
            
        return '-ERROR-'

def decompress_live_data_from_compressed_json(compressed_data):
    """Decompress and parse the live data from compressed GZIP JSON."""
    '''https://developer.samsung.com/health/android/data/api-reference/com/samsung/android/sdk/healthdata/HealthDataUtil.html#gettingDataFromCompressedJson'''
    try:
        # Decompress the data using gzip
        decompressed_data = gzip.decompress(compressed_data)

        # Parse the decompressed JSON
        live_data_list = json.loads(decompressed_data.decode('utf-8'))
        return live_data_list
    except Exception as e:
        print(f"Error decompressing or parsing JSON: {e}")
        return None

def save_live_data_to_excel(df, output_path):
    """Save the DataFrame to an Excel file for easy review."""
    
    global GUI
    if GUI == True:
        window['-STATUS-'].update('Saving Live Data to Excel')
        

    basename = os.path.splitext(output_path)[0]  # This will return the full path as the basename
    output_excel_path = basename + "_exercise_live_data.xlsx"

    try:
        df.to_excel(output_excel_path, index=False)
        print(f"Live Data successfully saved to {output_excel_path}")
    except Exception as e:
        print(f"Error saving live data to Excel: {e}")

def fetch_compressed_live_data(db_path):
    """Fetch the compressed live data from the Samsung Health exercise table."""
    '''https://developer.samsung.com/health/android/data/api-reference/com/samsung/android/sdk/healthdata/HealthConstants.Exercise.html#LIVE_DATA'''
    
    global GUI
    if GUI == True:
        window['-STATUS-'].update('Fetching Live Exercise Tracking Data')    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        query = """
        SELECT 
            _id,
            com_samsung_health_exercise_live__data
        FROM 
            com_samsung_health_exercise;
        """

        # Read the data from the database
        try:
            df = pd.read_sql_query(query, conn)
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite OperationalError (database locked): {e}")
            if GUI:
                window['-STATUS-'].update("Database is currently locked. Please ensure no other programs are accessing it and try again.")
            return False          

        # Decompress and parse each live data entry
        if GUI == True:
            window['-STATUS-'].update('Decompressing Live Exercise Tracking Data')        
        df['parsed_live_data'] = df['com_samsung_health_exercise_live__data'].apply(lambda x: decompress_live_data_from_compressed_json(x) if x else None)

        conn.close()
        return df[['_id', 'parsed_live_data']]  # Return _id and parsed_live_data columns
    except Exception as e:
        print(f"Error fetching or processing data: {e}")
        return None
    

def export_step_data(db_path, output_path):
    """Export data from the step count table in SHealth database to both Excel and HTML reports."""
    
    global GUI
    if GUI == True:
        window['-STATUS-'].update('Parsing Step Data')
        
    reporttype = 'Samsung Health Step Count Report'
    try:
        basename = os.path.splitext(output_path)[0]  # This will return the full path as the basename
        output_excel_path = basename + "_exercise_step_count.xlsx"
        output_html_path = basename + "_exercise_step_count.html"

        # Connect to the SQLite database
        try:
            conn = sqlite3.connect(db_path)
            logging.info(f"Successfully connected to database: {db_path}")
        except sqlite3.Error as e:
            logging.error(f"SQLite connection error: {e}")
            raise

        # Query to fetch the required data from step count table
        query = """
        SELECT 
            _id,
            datetime((last_modified_time + com_samsung_health_step__count_time__offset) / 1000, 'unixepoch') AS last_modified_datetime_with_offset,
            datetime((com_samsung_health_step__count_start__time + com_samsung_health_step__count_time__offset) / 1000, 'unixepoch') AS start_time_datetime_with_offset,
            datetime((com_samsung_health_step__count_update__time + com_samsung_health_step__count_time__offset) / 1000, 'unixepoch') AS update_time_datetime_with_offset,
            datetime((com_samsung_health_step__count_create__time + com_samsung_health_step__count_time__offset) / 1000, 'unixepoch') AS create_time_datetime_with_offset,
            datetime((com_samsung_health_step__count_end__time + com_samsung_health_step__count_time__offset) / 1000, 'unixepoch') AS end_time_datetime_with_offset,
            com_samsung_health_step__count_time__offset,
            com_samsung_shealth_tracker_pedometer__step__count_duration / 1000.0 AS step_count_duration_seconds,
            com_samsung_health_step__count_count,
            com_samsung_shealth_tracker_pedometer__step__count_run__step,
            com_samsung_shealth_tracker_pedometer__step__count_walk__step,
            com_samsung_health_step__count_speed AS step_count_speed_m_s,
            com_samsung_health_step__count_speed * 3.6 AS step_count_speed_kmh,
            com_samsung_health_step__count_distance AS step_count_distance_m,
            com_samsung_health_step__count_calorie,
            com_samsung_health_step__count_deviceuuid,
            last_modifying_device,
            sync_status
        FROM 
            com_samsung_health_step__count;
        """
        try:
            df = pd.read_sql_query(query, conn)
            logging.info("Data fetched successfully from the databases com_samsung_health_step__count table")
        except pd.io.sql.DatabaseError as e:
            logging.error(f"SQL query execution error for com_samsung_health_step__count: {e}")
            raise
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite OperationalError (database locked): {e}")
            if GUI:
                window['-STATUS-'].update("Database is currently locked. Please ensure no other programs are accessing it and try again.")
            return False      
        finally:
            conn.close()
    
        # Export to Excel file
        try:
            df.to_excel(output_excel_path, index=False)
            logging.info(f"Excel file successfully exported to {output_excel_path}")
        except Exception as e:
            logging.error(f"Error exporting data to Excel: {e}")
            raise
    
        # Prepare data for the HTML template
        columns = df.columns.tolist()
        data = df.values.tolist()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
        # Generate and export HTML report
        try:
            template = Template(html_template)
            rendered_html = template.render(columns=columns, data=data, timestamp=timestamp, reporttype=reporttype, script_version=script_version, company=company)
    
            with open(output_html_path, "w") as f:
                f.write(rendered_html)
            logging.info(f"HTML report successfully exported to {output_html_path}")
            print(f"HTML report successfully exported to {output_html_path}")
            
        except Exception as e:
            logging.error(f"Error generating or writing HTML report: {e}")
            raise
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise
    
    
    return True
    
def export_exercise_data(db_path, output_path):
    global GUI
    if GUI == True:
        window['-STATUS-'].update('Parsing Exercise Session Data')
        
    """Export data from the exercise table in SHealth database to both Excel and HTML reports."""
    reporttype = 'Samsung Health Exercise Session Report'
    try:
        basename = os.path.splitext(output_path)[0]  # This will return the full path as the basename
        output_excel_path = basename + "_exercise_session.xlsx"
        output_html_path = basename + "_exercise_session.html"

        # Connect to the SQLite database
        try:
            conn = sqlite3.connect(db_path)
            logging.info(f"Successfully connected to database: {db_path}")
        except sqlite3.Error as e:
            logging.error(f"SQLite connection error: {e}")
            raise

        # Query to fetch the required data from step count table
        query = """
        SELECT 
            _id,
            datetime((com_samsung_health_exercise_start__time + com_samsung_health_exercise_time__offset) / 1000, 'unixepoch') AS exercise_start_datetime_with_offset,
            datetime((com_samsung_health_exercise_end__time + com_samsung_health_exercise_time__offset) / 1000, 'unixepoch') AS exercise_end_datetime_with_offset,
            com_samsung_health_exercise_duration / 60000.0 AS exercise_duration_minutes,
            com_samsung_health_exercise_time__offset,
            com_samsung_health_exercise_exercise__type,
            com_samsung_health_exercise_distance AS com_samsung_health_exercise_distance_m,
            com_samsung_health_exercise_distance / 1000.0 AS com_samsung_health_exercise_distance_km,
            com_samsung_health_exercise_max__speed AS exercise_max_speed_m_s,
            com_samsung_health_exercise_mean__speed AS exercise_avg_speed_m_s,
            com_samsung_health_exercise_mean__speed * 3.6 AS exercise_avg_speed_kmh,
            com_samsung_health_exercise_count__type,
            com_samsung_health_exercise_calorie,
            com_samsung_shealth_exercise_source__type
        FROM 
            com_samsung_health_exercise;
        """
        try:
            df = pd.read_sql_query(query, conn)
            logging.info("Data fetched successfully from the databases com_samsung_health_exercise table")
        except pd.io.sql.DatabaseError as e:
            logging.error(f"SQL query execution error for com_samsung_health_exercise: {e}")
            raise
        
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite OperationalError (database locked): {e}")
            if GUI:
                window['-STATUS-'].update("Database is currently locked. Please ensure no other programs are accessing it and try again.")
            return False          
        finally:
            conn.close()

        # Map exercise type and count type to their descriptions
        df['com_samsung_health_exercise_exercise__type'] = df['com_samsung_health_exercise_exercise__type'].map(exercise_type_map)
        df['com_samsung_health_exercise_count__type'] = df['com_samsung_health_exercise_count__type'].map(exercise_count_type_map)
    
        # Handle any unmapped values (optional: replace NaN with 'Unknown')
        df['com_samsung_health_exercise_exercise__type'].fillna('Unknown', inplace=True)
        df['com_samsung_health_exercise_count__type'].fillna('Unknown', inplace=True)        
        
        # Export to Excel file
        try:
            df.to_excel(output_excel_path, index=False)
            logging.info(f"Excel file successfully exported to {output_excel_path}")
        except Exception as e:
            logging.error(f"Error exporting data to Excel: {e}")
            raise
    
        # Prepare data for the HTML template
        columns = df.columns.tolist()
        data = df.values.tolist()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
        # Generate and export HTML report
        try:
            template = Template(html_template)
            rendered_html = template.render(columns=columns, data=data, timestamp=timestamp, reporttype=reporttype, script_version=script_version, company=company)
    
            with open(output_html_path, "w") as f:
                f.write(rendered_html)
            logging.info(f"HTML report successfully exported to {output_html_path}")
            print(f"HTML report successfully exported to {output_html_path}")
        except Exception as e:
            logging.error(f"Error generating or writing HTML report: {e}")
            raise
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise    
    return True
######################################################################
'''
Begin MyWindow Class
Class to fix issue of Taskbar ICON not showing while window is maximized and using custom titlebar or no_titlebar=true
'''
######################################################################

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

if hasattr(windll.user32, "GetWindowLongPtrW"):
    _get_window_style = windll.user32.GetWindowLongPtrW
    _set_window_style = windll.user32.SetWindowLongPtrW
else:
    _get_window_style = windll.user32.GetWindowLongW
    _set_window_style = windll.user32.SetWindowLongW

class MyWindow(sg.Window):
    def __init__(self, *args, no_titlebar=False, **kwargs):
        self._no_titlebar = no_titlebar
        super().__init__(*args, **kwargs)

    def Finalize(self, *args, **kwargs):
        super().Finalize(*args, **kwargs)
        if self._no_titlebar:
            self.normal()

    def minimize(self):
        if self._no_titlebar:
            root = self.TKroot
            # clear override or Tcl will raise an error
            root.overrideredirect(False)
            # redraw the window to have something to show in the taskbar
            self.refresh()
            # catch the deinconify event
            root.bind("<Map>", self.normal)

        super().minimize()

    def normal(self, event=None):
        if self._no_titlebar:
            root = self.TKroot
            # set override to remove the titlebar
            root.overrideredirect(True)
            # set exstyle so that it shows in the taskbar
            hwnd = windll.user32.GetParent(root.winfo_id())
            style = _get_window_style(hwnd, GWL_EXSTYLE)
            style &= ~WS_EX_TOOLWINDOW
            style |= WS_EX_APPWINDOW
            _set_window_style(hwnd, GWL_EXSTYLE, style)
            # avoid infinite loop (withdraw + deiconify triggers a <Map>)
            root.unbind("<Map>")
            # re-assert window style
            root.withdraw()

        super().normal()

######################################################################
'''
End MyWindow Class
'''
######################################################################

def gui_mode():
    global GUI
    global window
    GUI = True
    """Run the program in GUI mode."""
    icon1= b'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'
    sg.theme('GRAYGRAYGRAY')
    right_click_menu = ['&Right', ['Cut', 'Copy', 'Paste', 'Quit']]
    layout = [
        [sg.Text("Samsung Health DB Parser", font=("Helvetica", 16))],
        [sg.Text("Select SQLite Database File:"), sg.Input(), sg.FileBrowse(key="-DB_PATH-")],
        [sg.Text("Select Output Folder:"), sg.Input(), sg.FolderBrowse(key="-OUTPUT_FOLDER-")],
        [sg.Text("Report Filename:"), sg.Input(key="-REPORT_FILENAME-", default_text="report")],
        [sg.Text(s=(40,1), k='-STATUS-', font=('Helvetica', 11, 'bold'), relief=sg.RELIEF_GROOVE)],
        [sg.Button("Generate Report", key="-GENERATE-"), sg.Button('Logs'),sg.Button("Quit"),sg.Push(), sg.Text(''),sg.Text(script_version, pad=((0,10),(0,10)), justification='right')]
    ]
    window = MyWindow("Breakpoint Forensics | Samsung Health DB Parser", layout, no_titlebar=False, right_click_menu=right_click_menu, alpha_channel=.99, grab_anywhere=True, modal=True, icon=icon1, finalize=True)
    window.bring_to_front()

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Quit":
            logging.info("GUI closed by user.")
            break
        if event == "-GENERATE-":
            db_path = values["-DB_PATH-"]
            output_folder = values["-OUTPUT_FOLDER-"]
            report_filename = values["-REPORT_FILENAME-"]

            if not db_path or not output_folder:
                sg.popup("Please select both a database file and output folder.", title="Input Error")
                logging.warning("User did not provide a database file or output folder.")
            else:
                report_path = os.path.join(output_folder, report_filename)
                try:
                    logging.info(f"Calling Ringleader")

                    window.perform_long_operation(lambda: process_ringleader(db_path, report_path), None)
                    
                except Exception as e:
                    logging.error(f"Error during report generation: {e}")
                    sg.popup(f"An error occurred: {str(e)}", title="Error")
        elif event == 'Cut':
            pyautogui.hotkey('ctrl', 'x')        
        
        elif event == 'Copy':
            pyautogui.hotkey('ctrl', 'c')
            
        elif event == 'Paste':
            pyautogui.hotkey('ctrl', 'v')
        
        ##Opens Log Folder in Explorer
        elif event == 'Logs':
            logpath = os.path.realpath(appdatalog)
            os.startfile(logpath)
        
        elif event == '-END KEY-':
            window['-STATUS-'].update('Processing Complete')
            logging.info('Processing Completed')
        
        elif event == '-ERROR-':
            sg.popup("An error occurred during processing.", title="Error")
            logging.info("Error occurred in processing.")
            
    window.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export data from a Samsung Health SQLite database to both a spreadsheet file and an HTML report.")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI version.")
    parser.add_argument("db_path", nargs="?", help="Path to the SQLite database file.")
    parser.add_argument("output_path", nargs="?", help="Path to the output report file.")

    args = parser.parse_args()

    # If no command-line arguments provided, default to GUI mode
    if not args.db_path and not args.output_path:
        logging.info("Launching GUI mode (no command-line arguments provided).")
        gui_mode()
    elif args.gui:
        logging.info("Launching GUI mode (GUI flag detected).")
        gui_mode()
    elif args.db_path and args.output_path:
        logging.info(f"Running in command-line mode with db_path: {args.db_path} and output_path: {args.output_path}")
        try:
            ringleader(args.db_path, args.output_path)
        except Exception as e:
            logging.error(f"Error occurred in command-line mode: {e}")
    else:
        parser.print_help()
