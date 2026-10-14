# HypoPG EXPLAIN on existing schemas

Full database: Kendall tau of HypoPG cost ranking vs measured time ranking: **0.43** over 33 configs.
Cost pick: `gpt-5-6-sol:customer_windows`. Time pick: `grok-4-7:small-dimension-filters`.

## Q22 (the query that decides top-1)

| schema | none cost | Grok cost | Opus cost | Grok/none | shape none | shape Grok | Grok shape = full Grok |
|---|---:|---:|---:|---:|---|---|---|
| full | 139924 | 137316 | 137316 | 0.981 | 31a6434ef5 | efd9f710cc | yes |
| tpcds_sf1_b0_p5 | 10636 | 9801 | 9801 | 0.922 | af4d5682ed | 9e7e5d7278 | no |
| tpcds_sf1_sys_p5 | 10360 | 9536 | 9536 | 0.920 | 8375f4701b | 424744a141 | no |
| tpcds_sf1_fk_p5 | 12323 | 9714 | 9714 | 0.788 | af4d5682ed | 9e7e5d7278 | no |
| tpcds_sf1_uitem_p5 | 12218 | 9610 | 9610 | 0.787 | af4d5682ed | 9e7e5d7278 | no |
| tpcds_sf1_strat_p5 | 12357 | 9749 | 9749 | 0.789 | af4d5682ed | 9e7e5d7278 | no |

## Plan-shape agreement and cost ranking

Shape ignores HypoPG index names. Cost tau is the sample's cost ranking vs the full database's cost ranking (both noise-free). Time tau is copied from the timed protocol.

| D' | shape agree | cost-sign agree | cost tau vs full cost | cost tau vs full time | cost pick |
|---|---:|---:|---:|---:|---|
| tpcds_sf1_b0_p5 | 254/3267 (8%) | 2730/3267 (84%) | 0.84 | 0.50 | grok-4-7:cross-channel-date-item |
| tpcds_sf1_sys_p5 | 287/3267 (9%) | 2730/3267 (84%) | 0.91 | 0.45 | grok-4-7:cross-channel-date-item |
| tpcds_sf1_fk_p5 | 395/3267 (12%) | 2803/3267 (86%) | 0.81 | 0.50 | grok-4-7:cross-channel-date-item |
| tpcds_sf1_uitem_p5 | 395/3267 (12%) | 2803/3267 (86%) | 0.81 | 0.50 | grok-4-7:cross-channel-date-item |
| tpcds_sf1_strat_p5 | 329/3267 (10%) | 2727/3267 (83%) | 0.82 | 0.49 | grok-4-7:cross-channel-date-item |

Full Grok Q22 shape_hash `efd9f710cc` (Index Only Scan on date_dim). Full none `31a6434ef5` (Seq Scan on date_dim).

