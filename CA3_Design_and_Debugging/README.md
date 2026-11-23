# CA-3 – OS Design & Debugging Challenge (research topic R19)

Student: Siril Saran B (25BTRCL254) · Course: 25PCCS201 Operating Systems · Faculty: Dr. Sujeet S Jagtap

Challenge F1 (defective LRU) + F2 (Belady's anomaly or bug) + a scan-resistant redesign (SLRU).

| Path | What |
|---|---|
| `docs/CA3_Report.pdf` / `.docx` / `.md` | the report |
| `ca3/bugs.py` | provided defective LRU, three fixes, oracles, six injected-fault mutants |
| `ca3/slru.py` | segmented-LRU design extension |
| `ca3/run_ca3.py` | all experiments, tables, figures (writes `ca3/results/`, `ca3/figures/`) |
| `ca3/test_ca3.py` | 8 unit tests |
| `ca3/build_report_ca3.py` | builds the report from the results |
| `src/` | page-replacement simulator and the seven ML-shaped trace generators (from CA-2) |

## Run
```
pip install -r requirements.txt
python -m unittest discover -s ca3 -p "test_ca3.py"
python ca3/run_ca3.py            # about 40 s
python ca3/build_report_ca3.py   # needs pandoc, LibreOffice (soffice), poppler (pdftotext) for the .docx/.pdf
```
