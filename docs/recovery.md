# Backup and recovery

Every backup creates a timestamped snapshot, then refreshes the selected repository files. Restore and Fish registration create a snapshot before changing managed files. Snapshot directories are private, outside the repository, and are never removed automatically.

```fish
ls ~/.local/state/dotfiles/backups
dots-restore --snapshot 20261103T210000.000000Z --dry-run
dots-restore --snapshot 20261103T210000.000000Z
```

Use an actual ID from your backup directory. `latest` chooses the most recent completed snapshot **before** making the pre-restore snapshot. That can be a pre-restore or pre-registration snapshot, not just a manual backup; use a specific ID when recovering an older state.

Snapshots retain raw file bytes and original modes, plus records of missing files and the two allowed theme symlinks. Recovery removes a managed file when it was absent in the chosen snapshot. Unmanaged files are never removed. Directory and unexpected-symlink conflicts stop the operation before any managed destination is changed.

`snapshot.json` is written last so interrupted snapshots are not selected automatically. Restoring writes each file atomically; a crash between files can leave a partially applied configuration. Run restore again, or restore the pre-change snapshot. Snapshots must match the current manifest; use the corresponding Git revision to recover a snapshot from before files were added/removed from the manifest.

The selected background is additionally saved as `selected-wallpaper` in manual backup snapshots, even when it originally lives outside the managed paths. Snapshot recovery restores the original setting paths exactly. If the original external image has since been deleted, recover that image from `selected-wallpaper`, or restore the repository version to use the bundled background.

Local snapshots are a recovery convenience on the same disk, not protection against disk loss. GitHub stores the reviewed repository copies only. Back up local recovery snapshots through your normal off-machine backup if you need that protection.

If a failed operation has already written some files, its pre-change snapshot remains available. A failed push leaves the commit and local snapshot intact. Never force-push to resolve an ordinary remote conflict: pull/rebase deliberately after reviewing local work.
