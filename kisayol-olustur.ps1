# 30A Studio: masaüstüne simgeli kısayol oluşturur (Housing Atlas'taki kisayol-olustur.ps1'den uyarlandı).
# Kısayol programı konsol penceresi açmadan başlatır (.venv\Scripts\pythonw.exe -X utf8 -m studio).
# "-X utf8" Python'u UTF-8 kipinde çalıştırır; baslat.bat bunu PYTHONUTF8=1 ile yapar, kısayol ortam değişkeni koyamaz.
# Bu dosya UTF-8 (BOM'lu) kaydedilir; BOM olmazsa Windows PowerShell 5.1 Türkçe harfleri bozar.
# Kullanım: powershell -NoProfile -ExecutionPolicy Bypass -File kisayol-olustur.ps1 [-Hedef KLASÖR]

param(
    [string]$Hedef = [Environment]::GetFolderPath("Desktop")
)

$ErrorActionPreference = "Stop"

# WScript.Shell kısayolları ANSI kod sayfasıyla (bu bilgisayarda 936) yazar; ş, ı, ö gibi harfler
# içeren yollarda hata verir ya da yolu bozar. Bu yüzden Windows'un Unicode arayüzü IShellLinkW kullanılır.
$shellLinkSource = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

namespace ThirtyAStudio
{
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    class ShellLink { }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
    interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder file, int size, IntPtr findData, uint flags);
        void GetIDList(out IntPtr idList);
        void SetIDList(IntPtr idList);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder name, int size);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string name);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder dir, int size);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string dir);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int size);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
        void GetHotkey(out short hotkey);
        void SetHotkey(short hotkey);
        void GetShowCmd(out int showCmd);
        void SetShowCmd(int showCmd);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder iconPath, int size, out int index);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string iconPath, int index);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string relativePath, int reserved);
        void Resolve(IntPtr hwnd, int flags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string file);
    }

    public static class Shortcut
    {
        public static void Save(string path, string target, string arguments, string workingDirectory,
                                string iconPath, string description)
        {
            IShellLinkW link = (IShellLinkW)new ShellLink();
            link.SetPath(target);
            link.SetArguments(arguments);
            link.SetWorkingDirectory(workingDirectory);
            link.SetIconLocation(iconPath, 0);
            link.SetDescription(description);
            ((IPersistFile)link).Save(path, true);
        }
    }
}
"@

# Add-Type sınıfı C# derleyicisiyle (csc.exe) %TEMP% içinde derler; derleyici bu yolu ANSI kod sayfasıyla okur.
# Kullanıcı klasörünün adında bu kod sayfasında olmayan harfler (ş, ı, ğ) varsa derleme başarısız olur. O zaman
# derleme geçici klasörün kısa (8.3) adıyla, o da olmazsa ortak kullanıcı klasöründeki bir klasörde yapılır.
function Test-AnsiPath([string]$Path) {
    $ansi = [Text.Encoding]::Default
    return $ansi.GetString($ansi.GetBytes($Path)) -ceq $Path
}

function Get-CompileTemp {
    $temp = [IO.Path]::GetTempPath()
    if (Test-AnsiPath $temp) {
        return $null
    }
    try {
        $short = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($temp).ShortPath
        if (Test-AnsiPath $short) {
            return $short
        }
    }
    catch { }
    $fallback = Join-Path $env:PUBLIC "ThirtyAStudioGecici"
    New-Item -ItemType Directory -Force -Path $fallback | Out-Null
    return $fallback
}

$repo = $PSScriptRoot
$pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    Write-Host "Önce baslat.bat dosyasını çalıştırın."
    exit 1
}

$shortcutPath = Join-Path $Hedef "30A Studio.lnk"
$savedTemp = $env:TEMP
$savedTmp = $env:TMP
try {
    $compileTemp = Get-CompileTemp
    if ($compileTemp) {
        $env:TEMP = $compileTemp
        $env:TMP = $compileTemp
    }
    Add-Type -TypeDefinition $shellLinkSource
    [ThirtyAStudio.Shortcut]::Save(
        $shortcutPath,
        $pythonw,
        "-X utf8 -m studio",
        $repo,
        (Join-Path $repo "studio\web\img\30a.ico"),
        "30A Studio"
    )
}
catch {
    Write-Host "Kısayol oluşturulamadı: $($_.Exception.GetBaseException().Message)"
    exit 1
}
finally {
    $env:TEMP = $savedTemp
    $env:TMP = $savedTmp
}

Write-Host "Kısayol oluşturuldu: $shortcutPath"
exit 0
