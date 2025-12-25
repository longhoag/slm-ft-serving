# Clinical Text Examples for Testing

This document provides sample clinical texts for testing the medical information extraction system. Each example includes the input text and expected output.

---

## Example 1: Melanoma with Brain Metastases

**Input:**
```
70-year-old man with widely metastatic cutaneous melanoma. PD-L1 was 5% on IHC and NGS reported TMB-high; BRAF testing was not performed prior to treatment. Given multiple symptomatic brain metastases he received combination immunotherapy with nivolumab plus ipilimumab and stereotactic radiosurgery to dominant intracranial lesions. Imaging after two cycles demonstrated some shrinking of index lesions but appearance of a new small lesion — overall assessment called a mixed response.
```

**Expected Output:**
- **Cancer Type:** melanoma (cutaneous)
- **Stage:** IV
- **Gene Mutation:** null
- **Biomarker:** PD-L1 5%; TMB-high
- **Treatment:** nivolumab and ipilimumab; stereotactic radiosurgery
- **Response:** mixed response
- **Metastasis Site:** brain

---

## Example 2: Early-Stage Breast Cancer

**Input:**
```
Patient diagnosed with stage 3 breast cancer with HER2 positive marker. Underwent mastectomy followed by adjuvant chemotherapy with trastuzumab and pertuzumab. Post-treatment scans show complete response with no evidence of disease.
```

**Expected Output:**
- **Cancer Type:** breast cancer
- **Stage:** 3
- **Gene Mutation:** null
- **Biomarker:** HER2 positive
- **Treatment:** mastectomy; trastuzumab and pertuzumab
- **Response:** complete response
- **Metastasis Site:** null

---

## Example 3: Lung Cancer with EGFR Mutation

**Input:**
```
62-year-old female with stage IV non-small cell lung cancer. Molecular testing revealed EGFR exon 19 deletion. Started on osimertinib with partial response after 3 months. Disease progressed with liver metastases after 18 months on therapy.
```

**Expected Output:**
- **Cancer Type:** non-small cell lung cancer
- **Stage:** IV
- **Gene Mutation:** EGFR exon 19 deletion
- **Biomarker:** null
- **Treatment:** osimertinib
- **Response:** partial response; disease progressed
- **Metastasis Site:** liver

---

## Example 4: Colorectal Cancer with KRAS Mutation

**Input:**
```
Stage III colorectal cancer with KRAS G12D mutation detected. Patient underwent surgical resection with negative margins. Adjuvant therapy with FOLFOX regimen completed. CEA levels normalized and patient remains disease-free at 2-year follow-up.
```

**Expected Output:**
- **Cancer Type:** colorectal cancer
- **Stage:** III
- **Gene Mutation:** KRAS G12D
- **Biomarker:** CEA
- **Treatment:** surgical resection; FOLFOX
- **Response:** disease-free
- **Metastasis Site:** null

---

## Example 5: Prostate Cancer with Bone Metastases

**Input:**
```
78-year-old male with metastatic castration-resistant prostate cancer. PSA level 145 ng/mL. Bone scan shows multiple skeletal metastases. Initiated on enzalutamide with PSA decline to 42 ng/mL after 6 months. Patient reports improved pain control and stable disease on imaging.
```

**Expected Output:**
- **Cancer Type:** prostate cancer (castration-resistant)
- **Stage:** metastatic
- **Gene Mutation:** null
- **Biomarker:** PSA 145 ng/mL
- **Treatment:** enzalutamide
- **Response:** stable disease
- **Metastasis Site:** bone (skeletal)

---

## Example 6: Ovarian Cancer with Peritoneal Spread

**Input:**
```
Stage IV high-grade serous ovarian carcinoma with peritoneal metastases and CA-125 of 892 U/mL. BRCA1 germline mutation identified. Underwent cytoreductive surgery followed by carboplatin and paclitaxel chemotherapy. Added olaparib maintenance therapy. CA-125 decreased to 18 U/mL with radiologic complete response.
```

**Expected Output:**
- **Cancer Type:** ovarian carcinoma (high-grade serous)
- **Stage:** IV
- **Gene Mutation:** BRCA1 germline mutation
- **Biomarker:** CA-125 892 U/mL
- **Treatment:** cytoreductive surgery; carboplatin and paclitaxel; olaparib
- **Response:** complete response
- **Metastasis Site:** peritoneal

---

## Example 7: Pancreatic Cancer

**Input:**
```
Patient with locally advanced pancreatic adenocarcinoma stage III. No distant metastases identified. Borderline resectable tumor involving the superior mesenteric artery. Received neoadjuvant FOLFIRINOX for 6 months with partial response allowing for Whipple procedure. Pathology confirmed R0 resection with negative lymph nodes.
```

**Expected Output:**
- **Cancer Type:** pancreatic adenocarcinoma
- **Stage:** III
- **Gene Mutation:** null
- **Biomarker:** null
- **Treatment:** FOLFIRINOX; Whipple procedure
- **Response:** partial response
- **Metastasis Site:** null

---

## Example 8: Renal Cell Carcinoma with Lung Metastases

**Input:**
```
Clear cell renal cell carcinoma stage IV with pulmonary metastases. Previous nephrectomy performed 2 years ago. Started on combination ipilimumab and nivolumab immunotherapy. Imaging after 4 cycles shows progressive disease with new liver lesions. Switched to cabozantinib with disease stabilization.
```

**Expected Output:**
- **Cancer Type:** renal cell carcinoma (clear cell)
- **Stage:** IV
- **Gene Mutation:** null
- **Biomarker:** null
- **Treatment:** ipilimumab and nivolumab; cabozantinib
- **Response:** progressive disease; disease stabilization
- **Metastasis Site:** lung (pulmonary); liver

---

## Example 9: Gastric Cancer with Lymph Node Involvement

**Input:**
```
Stage II gastric adenocarcinoma with regional lymph node involvement. HER2 testing positive by IHC 3+. Patient underwent total gastrectomy with D2 lymphadenectomy. Currently receiving adjuvant chemotherapy with capecitabine and oxaliplatin plus trastuzumab. Tolerating treatment well with no evidence of recurrence at 6 months.
```

**Expected Output:**
- **Cancer Type:** gastric adenocarcinoma
- **Stage:** II
- **Gene Mutation:** null
- **Biomarker:** HER2 positive (IHC 3+)
- **Treatment:** total gastrectomy; capecitabine and oxaliplatin; trastuzumab
- **Response:** no evidence of recurrence
- **Metastasis Site:** lymph nodes

---

## Example 10: Non-Medical Text (Negative Test Case)

**Input:**
```
The weather today is sunny with temperatures reaching 75 degrees. I went to the grocery store and bought apples, oranges, and bananas. Later, I plan to visit the park and meet my friends for a picnic.
```

**Expected Output:**
- **Cancer Type:** null
- **Stage:** null
- **Gene Mutation:** null
- **Biomarker:** null
- **Treatment:** null
- **Response:** null
- **Metastasis Site:** null
- **Note:** "No medical entities found in the provided text."

---

## Testing Notes

- Examples 1-9 cover various cancer types and clinical scenarios
- Example 10 tests the system's ability to handle non-medical text
- All examples use realistic clinical language and terminology
- Expected outputs may vary slightly depending on model interpretation
- Some fields returning null is expected when that information is not present in the text
