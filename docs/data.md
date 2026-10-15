# Data & methods

## Aluto volcano

Aluto is a peralkaline rhyolitic caldera complex in the central Main Ethiopian Rift, south of
Addis Ababa. It sits on the Wonji fault belt, the zone of active magmatic
rifting. It has erupted repeatedly in the Holocene and hosts Ethiopia's first producing
geothermal field (Aluto-Langano). InSAR has recorded episodes of uplift and subsidence,
which makes the interplay between the magmatic reservoir, the hydrothermal system and the
rift faults a central question.

## The ARGOS network

The **A**luto **R**egional **G**eophysical **O**bservation **S**tudy deployed up to 12
broadband stations from January 2012 to January 2014. The data are open at the EarthScope/IRIS
DMC.

| | |
|---|---|
| FDSN network | **XM** (2012–2014) |
| Channels | `HHZ`, `HHN`, `HHE` at 100 Hz, blank location code |
| Stations used | A01E, A02E, A03E, A04E, A05E, A07E, A09E, A10E, A11E, A12E, A13E |
| Workshop day | **15 November 2012**: all 11 stations operating (A13E installed 9 Oct 2012, A02E removed 22 Jan 2013) |

The full deployment history is in `data/metadata/stations_argos.csv` and plotted in
notebook 00.

## Velocity model

Association and location use the 1D model of Wilks et al. (2017, Table 1). It combines a
regional crustal model with geothermal well data. The top of the model is at 2.5 km above sea
level. Depths in all outputs are in **km below sea level**.

## Reference catalogue

Notebooks 04 and 05 compare the ML results with the manually reviewed ARGOS catalogue of
Yemane et al.: 2,393 events located between January 2012 and January 2014, mostly along the
Wonji fault belt and down to about 40 km depth, with b = 1.97 ± 0.10. They also use its analyst
picks. Files and formats are described in `data/reference/README.md`.

## Models

| Model | Weights | Reference |
|---|---|---|
| DeepDenoiser | `original`, `urban` | Zhu, Mousavi & Beroza (2019) |
| PhaseNet | `original`, `instance`, `stead`, **`volpick`** | Zhu & Beroza (2019); Zhong & Tan (2024) |
| EQTransformer | `original`, **`volpick`** | Mousavi et al. (2020); Zhong & Tan (2024) |
| PyOcto | — | Münchmeyer (2024) |

## Local magnitude

Keir et al. (2006) for the Ethiopian Rift:
$M_L = \log_{10}A + 1.196997\log_{10}(r/17) + 0.001066(r-17) + 2.0$,
with $A$ the zero-to-peak Wood-Anderson amplitude in mm (static magnification 2800, each
horizontal component measured separately) and $r$ the hypocentral distance in km.
