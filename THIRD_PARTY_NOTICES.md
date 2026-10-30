# Third-party notices and data provenance

## LeakProbe-owned material

The root [MIT License](LICENSE) applies to team-owned LeakProbe code and documentation. All code owners approved MIT and public redistribution on 30 October 2026. It does not replace third-party notices, grant model/API access or imply endorsement by EPA, Sandia, NVIDIA or Nebius.

## EPA Net3 model and WNTR

The bundled `data/networks/Net3.inp` is EPANET Example Network 3. Its content matches [WNTR 1.3.2's official example](https://github.com/USEPA/WNTR/blob/1.3.2/examples/networks/Net3.inp) after line-ending/trailing-newline normalization. The bundled file's SHA-256 is:

`ea3e825c4fef0b5cba47fb06301bc85253f18b6364dc96c44d9fb492c40faa52`

WNTR 1.3.2 is distributed under the Revised BSD License, with copyright held by National Technology & Engineering Solutions of Sandia, LLC and specified US Government rights. Its complete upstream copyright, conditions, disclaimer and included NumPy/EPANET notices are retained in [licenses/WNTR-1.3.2-LICENSE.md](licenses/WNTR-1.3.2-LICENSE.md), copied from the [official release license](https://github.com/USEPA/WNTR/blob/1.3.2/LICENSE.md). Keep these notices when redistributing the Net3 asset.

[EPA identifies its EPANET software as public domain](https://www.epa.gov/water-research/epanet). That statement is not used to assume that every downstream model, derivative library or dataset is public domain. The exact bundled model's upstream provenance and WNTR notices are retained separately. Do not imply EPA or Sandia endorsement.

## Generated datasets, reference profiles and evaluation artifacts

The two Net3 datasets, reference banks, monitoring caches and benchmark outputs are team-generated simulation artifacts based on that model, not private utility measurements or third-party customer data. Their generator configuration, split assignments, truth labels and saved results remain unchanged. Permission to redistribute the team's own material was confirmed by the owners. The underlying Net3 notices continue to apply; the root license does not claim exclusive ownership of the upstream network model.

All five original investigation traces are retained, including invalid and legacy attempts. Their observations are simulated, not field-verified leaks. Provider response/request identifiers in traces are correlation metadata, not API credentials. No model weights, private review databases, populated Secrets files or third-party dataset downloads are included. Root MIT permission for team-owned material does not establish copyright ownership of all model-generated prose.

## NVIDIA Nemotron and Nebius

The application calls the hosted model identifier `nvidia/nemotron-3-super-120b-a12b`. It does not redistribute NVIDIA weights. NVIDIA's [Nemotron 3 Super model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) identifies the [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/). Model access/use remains subject to those terms; the model is not relicensed as MIT by this repository.

Nebius Token Factory provides the remote inference service. API use, credits and handling of submitted content are governed by the account's applicable [Nebius agreement](https://docs.nebius.com/legal/agreement), [Token Factory supplemental terms](https://docs.nebius.com/legal/token-factory) and model conditions. Older Token Factory terms have transitional applicability to some reserved accounts; this review does not verify the owner's individual service contract. A public source license grants neither service credits nor unrestricted API usage. Keep keys private and disclose only synthetic evidence in this demo.

## Installed dependencies

The release installs Python packages from their distributions; it does not vendor their source trees, wheels or shared libraries. Their own distributions carry their licenses and notices. Important direct dependencies are Streamlit, Altair, WNTR, NumPy, pandas, jsonschema, PyArrow, setuptools and the OpenAI-compatible Python SDK; optional research/test dependencies include scikit-learn, imbalanced-learn, python-dotenv and vl-convert-python. Their pinned/runtime declarations remain unchanged.

The root MIT license does not relicense these packages. A binary/container distribution would need a separate inventory of bundled transitive libraries and their notices; this source-release review is not a binary redistribution clearance or a vulnerability assessment.
