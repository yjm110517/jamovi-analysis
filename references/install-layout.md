# Jamovi Install Layout

Use this file to confirm the verified local entry points for jamovi on this machine.

## Default install root

- `C:\Program Files\jamovi 2.6.19.0`

## Verified executables

- GUI app: `bin\jamovi.exe`
- Bundled R: `Frameworks\R\bin\x64\Rscript.exe`
- Bundled Python: `Frameworks\python\python.exe`

## Verified module roots

- Base R libraries: `Resources\modules\base\R`
- Statistical analysis module: `Resources\modules\jmv\R`
- Analysis YAML definitions: `Resources\modules\jmv\analyses`
- Server package: `Resources\server\jamovi\server`

## Verified server command

The jamovi install's `bin\env.conf` defines the server entry point as:

- `..\Frameworks\python\python -u -Xutf8 -m jamovi.server 0 --stdin-slave`

The wrapper script reproduces the environment variables from that config so the server can be launched outside the GUI bootstrap.

## Verified analysis calls

The following calls were executed successfully against the local install:

- `ttestIS(formula = len ~ supp, data = ToothGrowth)`
- `descriptives(data = mtcars, vars = c("mpg", "disp"), mean = TRUE, sd = TRUE, n = TRUE, missing = TRUE)`

## Practical implication

- Use bundled R plus `library(jmv)` for deterministic, scriptable analysis work.
- Use `jamovi.server` only when the task genuinely needs an interactive jamovi session.
