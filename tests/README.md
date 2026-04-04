# NSU Audit Engine Tests

Run all tests:
```bash
cd packages/cli
python -m pytest ../../tests/test_audit.py -v
```

Run specific test class:
```bash
python -m pytest ../../tests/test_audit.py::TestLevel1 -v
```

## Test Coverage

### Level 1: Credit Tallying
- Basic credit counting
- Retake resolution (keeps best grade)
- Failed course handling
- Withdrawn course handling
- Incomplete grades
- Illegal retake detection (B+ or higher)
- Transfer waiver credits

### Level 2: CGPA & Standing
- Simple CGPA calculation
- CGPA truncation (NSU rule: never round up)
- Probation detection
- Normal standing
- Semester ordering
- Waiver exclusion from GPA

### Level 3: Graduation Audit
- Program knowledge parsing
- Eligible student detection
- Missing course detection
- Low CGPA ineligibility

### Edge Cases
- Empty transcript
- All withdrawals
- Case-insensitive grades
- All grade points accounted
