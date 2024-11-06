# Samsung-Secure-Health-Data-Parser-
Parse and Generated Reports from Samsung Health Database Structures and Compressed JSON Data

**Overview**
The Samsung Secure Health Data Parser is a forensic tool designed to extract and analyze data from Samsung Health databases. With the increasing importance of health-related data in digital forensics, this tool simplifies the process of extracting critical information, such as exercise data, step counts, and live activity tracking, stored in Samsung Health databases.
The tool offers both a GUI and command-line interface.

**Features**
•	Step Count Parsing: Extract step count data and output the results in both Excel and HTML formats.
•	Exercise Session Analysis: Gather details such as exercise type, duration, distance, and calories burned for individual sessions.
•	Live Data Decompression: Decompresses and parses GZIP-compressed JSON data stored during live exercise tracking sessions.
•	Open Source and Modular Functionality: Allows easy expansion or integration of functions into other tools/scripts.
•	Comprehensive Reports: Generates reports in Excel and HTML formats for easy review and analysis.
•	Precompiled Windows GUI Builds: Precompile builds for easy execution without needing to download or setup additional dependencies.
•	Command-Line Support: For advanced users, the tool also supports command-line arguments for seamless integration into automated workflows.

________________________________________
****Samsung Health Database Path & Decryption
**
**By default, Samsung Health stores its databases in a protected path on Android devices:


_/data/data/com.sec.android.app.shealth/databases/SecureHealthData.db
_
This database is encrypted by default and cannot be directly accessed without proper decryption. Fortunately, forensic tools like Cellebrite Physical Analyzer automatically decrypt the Samsung Health database during a forensic extraction, if the encryption keys were recovered. The decrypted version of the database is stored at:


_/data/data/com.sec.android.app.shealth/databases/SecureHealthData.db/SecureHealthData.db.decrypted
_

Before using this script, users must manually export this decrypted version of the database. Once exported, this decrypted database can be parsed using the Samsung Secure Health Data Parser to generate detailed reports.


GUI and Command-Line Modes
GUI Mode
The GUI interface simplifies the user experience:
•	File selection for the decrypted database and output folder.
•	Status updates that show progress during data extraction.
•	Access to logs for troubleshooting or reviewing detailed logs of the process.
Command-Line Mode
For more technical users, the command-line mode provides an efficient way to run the tool as part of larger forensic workflows. Use the following command:


_python samsung_secure_health_data_parser.py <db_path> <output_path>
_
Or launch the GUI by executing the program with no arguments.
________________________________________
How to run it:

Precompiled exe builds are available at breakpointforensics.com/tools

Or can be run/compiled as follows from source:

Prerequisites
Before running this tool, ensure you have:
1.	A decrypted version of the Samsung Health database from Cellebrite Physical Analyzer or another forensic tool. The decrypted database should be found at:
_/data/data/com.sec.android.app.shealth/databases/SecureHealthData.db/SecureHealthData.db.decrypted
_

3.	Python 3.11 or greater installed on your system.
   
5.	Install the required dependencies using the following command:

_pip install pandas pyautogui FreeSimpleGUI openpyxl jinja2
_
