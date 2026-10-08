| D' | score | configs | tau | 95% CI | top-1 | regret | top-3 hit | cost reduction | incl. sample build | D' pick | full-database best |
|---|---|---:|---:|---|---|---:|---|---:|---:|---|---|
| tpcds_sf1_b0_p5 | A runtime | 33 | 0.508 | [0.26, 0.72] | no | 1.014 | yes | 42.6x | 25.2x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_b0_p5 | B build+runtime | 33 | 0.583 | [0.37, 0.75] | no | 1.012 | yes | 42.6x | 25.2x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_sys_p5 | A runtime | 33 | 0.462 | [0.20, 0.69] | no | 1.014 | yes | 89.5x | 32.6x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_sys_p5 | B build+runtime | 33 | 0.636 | [0.44, 0.79] | no | 1.012 | yes | 89.5x | 32.6x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_uitem_p5 | A runtime | 33 | 0.451 | [0.27, 0.63] | no | 1.014 | yes | 2.6x | 2.5x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_uitem_p5 | B build+runtime | 33 | 0.47 | [0.20, 0.71] | no | 1.012 | yes | 2.6x | 2.5x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_fk_p5 | A runtime | 33 | 0.42 | [0.17, 0.62] | no | 1.014 | yes | 3.5x | 3.3x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_fk_p5 | B build+runtime | 33 | 0.447 | [0.20, 0.66] | no | 1.012 | yes | 3.5x | 3.3x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_strat_p5 | A runtime | 33 | 0.28 | [-0.01, 0.56] | yes | 1.0 | yes | 3.4x | 3.2x | grok-4-7:small-dimension-filters | grok-4-7:small-dimension-filters |
| tpcds_sf1_strat_p5 | B build+runtime | 33 | 0.371 | [0.08, 0.63] | no | 1.012 | yes | 3.4x | 3.2x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_b0_p5_c4 | A runtime | 33 | 0.242 | [0.01, 0.50] | no | 1.014 | no | 29.5x | 19.9x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_b0_p5_c4 | B build+runtime | 33 | 0.314 | [0.08, 0.55] | no | 1.012 | no | 29.5x | 19.9x | claude-opus-5:light_dimension_covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_uitem_p5_c4 | A runtime | 33 | 0.295 | [0.03, 0.52] | no | 1.078 | yes | 2.4x | 2.3x | composer-2-5:aggressive-mixed-covering | grok-4-7:small-dimension-filters |
| tpcds_sf1_uitem_p5_c4 | B build+runtime | 33 | 0.231 | [0.00, 0.47] | no | 1.099 | yes | 2.4x | 2.3x | composer-2-5:aggressive-mixed-covering | grok-4-7:small-dimension-filters |
