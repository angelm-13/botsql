# Travis CI y calidad backend

## Uso local

```bash
cd backend
bash ci/install_ci.sh
bash ci/run_all_checks.sh
```

Incluye black, isort, flake8, pycodestyle/PEP8, pydocstyle, import checks, bandit, pip check, pip-audit, link checker y unittest con coverage.

Para validar links remotos:

```bash
CHECK_REMOTE_LINKS=1 bash ci/check_links.sh
```
