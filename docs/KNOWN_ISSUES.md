# Known issues

These application issues are documented as TODO comments and remain unfixed.
Use a temporary home directory or disposable configuration when reproducing them.

## Failed configuration writes can lose saved devices

Add, update, and delete call `viper.WriteConfig`, which truncates the existing
file before writing its replacement. A failed write can leave invalid JSON and
lose the previous configuration.

Example: with a disposable configuration, limit the process's file size below
the JSON output size and update a device. The command reports a write error,
but the original file has already been truncated. The review reproduced this
with a 64-byte limit.

Until fixed, keep a backup before making changes. Fixing this requires changing
the application's persistence logic to write a new file first, then replace the
original after the write succeeds, with replacement behavior checked on all OSes.

TODO location: `cmd/device/update.go`, next to `viper.WriteConfig`; it also applies
to add and delete.

## Concurrent commands can overwrite each other's changes

Each command reads the configuration before changing it. Another process can
save changes before the first process writes its old snapshot back.

Example, starting with a saved `old-pc`:

1. In terminal A, run `wwss device delete old-pc` and leave its prompt unanswered.
2. In terminal B, add `new-pc` and wait for the command to finish.
3. Confirm deletion in terminal A.
4. `new-pc` is also removed from the saved configuration.

Until fixed, run one device mutation command at a time, including across SSH
sessions. Fixing this requires reloading and applying a mutation under a
cross-process lock after confirmation.

TODO location: `cmd/device/delete.go`, before deleting the map entry; it also
applies to add and update.

## Dotted device names can create phantom devices

Viper treats dots as configuration path separators. Adding a dotted name and
then writing the device map again can introduce incomplete nested entries.

Example, using a disposable configuration:

```sh
wwss device add --name office.pc --ipv4 192.0.2.20 --mac 02:00:00:00:00:01
wwss device add --name other --ipv4 192.0.2.30 --mac 02:00:00:00:00:02
wwss device list
```

An extra `office` entry can appear. The review reproduced this in 13 of 20 runs;
it is intermittent because map iteration order affects serialization.

Until fixed, use names containing letters, digits, hyphens, or underscores.
Fixing this requires validating names or storing device keys independently of
Viper's path syntax.

TODO location: `cmd/device/add.go`, before normalizing the device name.

## Optional CLI additions requiring application changes

- `--version`: add a Cobra version value and build metadata injection.
- `--config`: add an explicit path option to configuration initialization.

Neither option is required to package the existing application. Release filenames
carry the version, and the existing home-directory configuration path is preserved.
