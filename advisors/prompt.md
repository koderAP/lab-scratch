# Task for an index advisor

You are acting as a database index advisor for a PostgreSQL 14 database that holds the TPC-DS benchmark at scale factor 1 (about 1 GB of data). You propose index configurations for the whole workload. You do not run anything against a database.

## Inputs (read these files)

- Table definitions and row counts: `/Users/anubhaviitd/Desktop/Sampling_COL868/advisors/schema_tables.txt`
- Indexes that already exist (do not propose these again): `/Users/anubhaviitd/Desktop/Sampling_COL868/advisors/existing_indexes.txt`
- The workload: the 99 TPC-DS queries in PostgreSQL dialect, one per file, `/Users/anubhaviitd/Desktop/Sampling_COL868/workloads/tpcds/01.sql` through `99.sql`. Read as many as you need. The whole workload, all 99 queries, is run against every configuration, and the score of a configuration is the total runtime of all 99 queries plus the time to build its indexes.

## What to produce

Propose exactly **5 index configurations**. A configuration is a set of 1 to 8 indexes that would be created together, then the whole workload runs. Make the 5 configurations meaningfully different from each other, for example by size (small and conservative up to aggressive), by which tables they target, or by the strategy behind them. Say in one sentence per configuration what it is trying to do.

Rules for indexes:
- B-tree indexes only, on the tables in the schema file. Use real column names from the schema.
- Single-column or multi-column (up to 4 columns). Column order matters. A covering `include` list is allowed (PostgreSQL `INCLUDE`).
- Do not repeat an index that already exists.
- Do not put an index on a table with fewer than 1000 rows.
- No partial indexes, no expression indexes, no other index types.

## Output

Write exactly one JSON file, at the path given to you in the instructions that came with this prompt, in this form, and nothing else:

```json
{
  "model": "<your model name>",
  "configs": [
    {
      "name": "short label",
      "rationale": "one sentence",
      "indexes": [
        {"table": "store_sales", "columns": ["ss_item_sk", "ss_sold_date_sk"], "include": []}
      ]
    }
  ]
}
```

Check before finishing that the JSON parses, there are exactly 5 configurations, and every table and column name appears in the schema file. In your final message reply with one line: the path you wrote and the number of configurations.

## Files you may open

Only the three inputs listed above (the two text files in `advisors/` and the query files in `workloads/tpcds/`). Do not open anything under `results/`, `scripts/`, `docs/` or `tasks/`, and do not look at other advisors' output. The only file you create is your JSON output.
