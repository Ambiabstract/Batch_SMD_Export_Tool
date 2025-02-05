macroscript Ambi_Export_SMD_start
category:"Ambiabstract_scripts"
buttontext:"Ambi_Export_SMD_start"
tooltip:"Ambi_Export_SMD_start"

(
    -- Initialize Python
    python.Init()

    -- Execute the Python script with the correct path
    python.ExecuteFile @"C:/Program Files/Autodesk/3ds Max 2023/scripts/Ambi_Export_SMD.py"

    -- Log errors if they occur
    if python.GetLastError() != "" do
        print python.GetLastError()
)
