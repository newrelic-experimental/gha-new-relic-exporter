# WORK IN PROGRESS

Configure your New Relic API Key as `NEW_RELIC_API_KEY` and Github token as `GHA_TOKEN` in your repository secrets

Add `new-relic-exporter.yaml` to .github/workflows, example below

```
name: new-relic-exporter

on:
  workflow_run:
    workflows: ['*']
    types: [completed] # defaults to run on every completed workflow run event
  
env:
  GHA_TOKEN: ${{ secrets.GHA_TOKEN }}
  NEW_RELIC_API_KEY: ${{ secrets.NEW_RELIC_API_KEY }}
  GHA_RUN_ID: ${{ github.event.workflow_run.id }}
  GHA_RUN_NAME: ${{ github.event.workflow_run.name }}

jobs:
  new-relic-exporter:
    name: new-relic-exporter
    runs-on: ubuntu-latest
    if: ${{ always() }}
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: new-relic-exporter
        uses: dpacheconr/gha-new-relic-exporter@latest
```
