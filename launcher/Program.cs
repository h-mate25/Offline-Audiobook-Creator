using System.ComponentModel;
using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Windows.Forms;

internal static class Program
{
    private const int Port = 8766;
    private const string UiUrl = "http://127.0.0.1:8766";

    [STAThread]
    private static void Main()
    {
        var logPath = Path.Combine(AppContext.BaseDirectory, "launcher.log");

        try
        {
            AppendLog(logPath, "Launcher started.");
            var root = FindProjectRoot();
            logPath = Path.Combine(root, "launcher.log");
            AppendLog(logPath, $"Project root: {root}");
            EnsureDocker(root, logPath);
            StartCompose(root, logPath);
            WaitForUi(logPath);
            Process.Start(new ProcessStartInfo { FileName = UiUrl, UseShellExecute = true });
            AppendLog(logPath, $"Browser opened: {UiUrl}");
        }
        catch (Exception exception)
        {
            AppendLog(logPath, exception.ToString());
            MessageBox.Show(
                $"Az Offline Audiobook Creator nem tudott elindulni.\n\n{exception.Message}\n\nRészletek: {logPath}",
                "Offline Audiobook Creator",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }

    private static string FindProjectRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "docker-compose.yml")))
                return directory.FullName;
            directory = directory.Parent;
        }

        throw new InvalidOperationException(
            "A docker-compose.yml nem található. Az indítót a projekt mappájából futtasd.");
    }

    private static void EnsureDocker(string root, string logPath)
    {
        if (!IsDockerReady(root, logPath))
        {
            AppendLog(logPath, "Docker Desktop indítása...");
            RunProcess("docker", ["desktop", "start"], root, logPath, TimeSpan.FromSeconds(30));
        }

        var deadline = DateTime.UtcNow.AddMinutes(2);
        while (DateTime.UtcNow < deadline)
        {
            if (IsDockerReady(root, logPath)) return;
            Thread.Sleep(1000);
        }

        throw new InvalidOperationException(
            "A Docker Desktop nem állt készen két percen belül. Indítsd el a Docker Desktopot, majd próbáld újra.");
    }

    private static bool IsDockerReady(string root, string logPath)
    {
        var result = RunProcess("docker", ["info"], root, logPath, TimeSpan.FromSeconds(10), false);
        return result.ExitCode == 0;
    }

    private static void StartCompose(string root, string logPath)
    {
        AppendLog(logPath, "Docker Compose konténer indítása...");
        var result = RunProcess(
            "docker", ["compose", "up", "-d", "--build"], root, logPath, TimeSpan.FromMinutes(30));

        if (result.ExitCode != 0)
        {
            throw new InvalidOperationException(
                "A Docker konténer indítása sikertelen volt. Ellenőrizd a launcher.log fájlt.");
        }
    }

    private static void WaitForUi(string logPath)
    {
        AppendLog(logPath, "A webes felület elérhetőségének ellenőrzése...");
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
        var deadline = DateTime.UtcNow.AddMinutes(3);

        while (DateTime.UtcNow < deadline)
        {
            try
            {
                using var response = client.GetAsync($"{UiUrl}/api/settings").GetAwaiter().GetResult();
                if (response.IsSuccessStatusCode) return;
            }
            catch (HttpRequestException) { }
            catch (TaskCanceledException) { }

            Thread.Sleep(1000);
        }

        throw new InvalidOperationException(
            "A konténer elindult, de a webes felület nem vált elérhetővé három percen belül.");
    }

    private static ProcessResult RunProcess(
        string fileName,
        IReadOnlyList<string> arguments,
        string workingDirectory,
        string logPath,
        TimeSpan timeout,
        bool setPort = true)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };

        foreach (var argument in arguments) startInfo.ArgumentList.Add(argument);
        if (setPort) startInfo.Environment["AUDIOBOOK_PORT"] = Port.ToString();

        using var process = new Process { StartInfo = startInfo };
        try
        {
            if (!process.Start())
                throw new InvalidOperationException($"Nem indítható el a(z) {fileName} parancs.");
        }
        catch (Win32Exception exception)
        {
            throw new InvalidOperationException(
                $"A(z) {fileName} nem található. Telepítsd a Docker Desktopot, majd próbáld újra.",
                exception);
        }

        var stdout = process.StandardOutput.ReadToEndAsync();
        var stderr = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit((int)timeout.TotalMilliseconds))
        {
            try { process.Kill(true); } catch { }
            throw new TimeoutException($"A(z) {fileName} parancs túllépte a megengedett időt.");
        }

        Task.WaitAll(stdout, stderr);
        var output = new StringBuilder();
        output.AppendLine($"> {fileName} {string.Join(" ", arguments)}");
        output.AppendLine(stdout.Result);
        output.AppendLine(stderr.Result);
        AppendLog(logPath, output.ToString());
        return new ProcessResult(process.ExitCode);
    }

    private static void AppendLog(string path, string message)
    {
        try
        {
            File.AppendAllText(path, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}{Environment.NewLine}");
        }
        catch { }
    }

    private readonly record struct ProcessResult(int ExitCode);
}

