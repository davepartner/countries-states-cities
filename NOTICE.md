# Notice

## Derivative work

This repository is a derivative of the **Countries States Cities Database**
(https://github.com/dr5hn/countries-states-cities-database), © dr5hn,
distributed under the Open Database License v1.0 (ODbL).

Changes made here:

- Replaced surrogate numeric identifiers (`id`, `*_id` foreign keys) with
  natural keys (`country_code`, ISO 3166-2 `code`, Wikidata QID or stable slug).
- Split the conflated `type` field into `kind` + `type` (+ `type_local`).
- Removed the `gdp` field; added `population_year` and made `phone` a list.
- Replaced the PHP/MySQL/Node export pipeline with a single Python exporter.
- Rewrote the documentation.

Under ODbL, this derivative is distributed under the same license (see
[LICENSE](LICENSE)).

## Upstream sources

Individual records carry names and coordinates copied from open sources that
require attribution. The full source register — publishers, licences, required
credits, and the changes applied — is in
[LICENSES/SOURCES.txt](LICENSES/SOURCES.txt).

Keep [LICENSES/SOURCES.txt](LICENSES/SOURCES.txt) and the accompanying licence
notices with all copies of the data, and pass them on to recipients. The
principal upstream sources are:

- [GeoNames](https://www.geonames.org/) (CC BY 4.0)
- © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL 1.0)
- [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing) (CC0)
- National postal and statistical registers (see SOURCES.txt for the full list)

Country names in some languages follow
[Unicode CLDR](https://cldr.unicode.org/): © 2015–2024 Unicode, Inc., under the
Unicode License v3 (see [LICENSES/Unicode-3.0.txt](LICENSES/Unicode-3.0.txt)),
whose notice must travel with copies.
