# Verification

Initial verification on CachyOS, 2026-11-03:

- 20 isolated tests covering backup/restore, permissions, absent files, profile isolation, private preference handling, wallpaper capture, Fish wrappers, dry-run, symlink refusal, snapshot validation, and a rejected Git push followed by a successful retry.
- Bash syntax and ShellCheck pass. Fish scripts parse. Both profiles pass niri 26.04 and Noctalia 5.4.1 validators.
- A nested niri session with a fresh temporary home rendered Noctalia, the bundled wallpaper, the selected palette, Kitty, and Fuzzel. Screenshot-to-clipboard bytes round-tripped successfully.
- That smoke test found and fixed the obsolete Fuzzel `icons=yes` setting, the unwanted automatic light theme, and an enabled Hyprland template on a niri desktop.
- Keyboard input in the nested window was not verified end to end. Fuzzel held exclusive keyboard focus during the launcher check. The nested environment also emitted portal/systemd-service warnings and is not a substitute for a real login session.
- The existing desktop was migrated with pre-change snapshots. Fish commands load, local GHCup initialization remains available, Noctalia reports dark mode and the bundled wallpaper, and the monitor remains at 2560×1440/165 Hz with VRR. Backup followed by restore dry-run reports no changes.

A fresh CachyOS VM installation, package-installation prompts, reboot/login, display-manager integration, lock-screen authentication, and portal behavior in a fresh login have **not** been tested. No VM image was available in this workspace. The automated tests and nested session use already-installed packages on the host.
