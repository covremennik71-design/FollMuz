' FollMuz - Hidden Web Server Launcher
' This script runs the server without a visible console window

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Navigate to script folder
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptPath

' Check if app.py exists
If Not fso.FileExists("app.py") Then
    MsgBox "File app.py not found!" & vbCrLf & vbCrLf & _
           "Make sure the script is in the FollMuz2 folder", _
           vbCritical, "FollMuz - Error"
    WScript.Quit
End If

' Check if Python is available
On Error Resume Next
Set exec = WshShell.Exec("python --version")
pyVersion = exec.StdOut.ReadLine()
If Err.Number <> 0 Then
    MsgBox "Python not found!" & vbCrLf & vbCrLf & _
           "Install Python from https://www.python.org/" & vbCrLf & _
           "Make sure to check 'Add Python to PATH'", _
           vbCritical, "FollMuz - Error"
    WScript.Quit
End If
On Error GoTo 0

' Check if port 5000 is busy and kill old process
On Error Resume Next
res = WshShell.Run("powershell -Command ""try { (Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -TimeoutSec 1 -UseBasicParsing).StatusCode -eq 200 } catch { exit 1 }""", 0, True)
If res = 0 Then
    WshShell.Run "cmd /c taskkill /IM pythonw.exe /F", 0, True
    WScript.Sleep 1000
End If
On Error GoTo 0

' Delete old error log
If fso.FileExists("error.log") Then fso.DeleteFile("error.log")

' Start server hidden via cmd /c
WshShell.Run "cmd /c pythonw.exe app.py > error.log 2>&1", 0, False

' Wait and check server with retries (up to 10 attempts, 1 second each)
serverOK = False
For i = 1 to 10
    WScript.Sleep 1000
    On Error Resume Next
    res = WshShell.Run("powershell -Command ""try { (Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -TimeoutSec 1 -UseBasicParsing).StatusCode -eq 200 } catch { exit 1 }""", 0, True)
    If res = 0 Then
        serverOK = True
        Exit For
    End If
    On Error GoTo 0
Next

If serverOK Then
    ' Server started successfully - open browser
    WshShell.Run "http://127.0.0.1:5000", 1, False
Else
    ' Server failed - show error dialog with log details
    errorMsg = "Server failed to start!" & vbCrLf & vbCrLf
    
    If fso.FileExists("error.log") Then
        Set logFile = fso.OpenTextFile("error.log", 1)
        If Not logFile.AtEndOfStream Then
            logContent = logFile.ReadAll()
            errorMsg = errorMsg & "Error log:" & vbCrLf & _
                       "========================================" & vbCrLf & _
                       logContent & vbCrLf & _
                       "========================================"
        End If
        logFile.Close
    End If
    
    errorMsg = errorMsg & vbCrLf & vbCrLf & _
               "Try running run.bat for diagnostics."
    
    MsgBox errorMsg, vbCritical, "FollMuz - Startup Error"
End If

Set WshShell = Nothing
Set fso = Nothing
