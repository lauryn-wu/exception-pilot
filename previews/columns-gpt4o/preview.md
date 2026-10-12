# Column study preview — no API calls

24 previously inspected worlds × 2 record variants × 4 column sets × 3 arms = 576 calls.
All 576 exact requests are in preview.json. Below are all 24 requests from the first world.
Headings and answer keys are for inspection and are never added to provider messages.

## ex-list-000/record_2/description/copy_class

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | C |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/other_attributes/copy_class

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/other_attributes/cot

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/minimal/cot

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | B |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/description/direct

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | C |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_1/minimal/direct

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | B |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_2/full/cot

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/description/cot

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | B |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/full/direct

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_2/description/cot

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | C |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/description/copy_class

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | B |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/description/direct

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Verified class |
|---|---|---|
| EEF3UM | Equipped with snow tracks | B |
| EBV2LA | Designed for frozen terrain | C |
| EGK6P3 | Operates in tropical forests | A |
| EZKZXD | Designed for humid summers | B |
| ED9BUV | Used at an equatorial station | A |
| E9PUA6 | Used at an Arctic station | B |
| EJZ6T8 | Built for subzero temperatures | B |
| EWEC56 | Equipped for hot sand | A |
| EP3ARK | Operates on polar ice | C |
| EZ3K2B | Built for desert heat | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_2/minimal/cot

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | C |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/full/copy_class

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/minimal/copy_class

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | B |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/other_attributes/direct

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_2/minimal/copy_class

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | C |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_1/other_attributes/copy_class

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/minimal/direct

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Verified class |
|---|---|
| EEF3UM | B |
| EBV2LA | C |
| EGK6P3 | A |
| EZKZXD | C |
| ED9BUV | A |
| E9PUA6 | B |
| EJZ6T8 | B |
| EWEC56 | A |
| EP3ARK | C |
| EZ3K2B | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_2/other_attributes/cot

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/full/copy_class

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/full/direct

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```

## ex-list-000/record_1/full/cot

Recorded: B; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| EEF3UM | Equipped with snow tracks | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Designed for frozen terrain | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Operates in tropical forests | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Designed for humid summers | Automatic | Vinyl | Two | Z | B |
| ED9BUV | Used at an equatorial station | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Used at an Arctic station | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Built for subzero temperatures | Manual | Vinyl | Four | X | B |
| EWEC56 | Equipped for hot sand | Manual | Vinyl | Four | Z | A |
| EP3ARK | Operates on polar ice | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Built for desert heat | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Think step by step, then put ANSWER: followed by A, B, or C alone on the final line.
```

## ex-list-000/record_2/other_attributes/direct

Recorded: C; background-pattern label: A; row: 4.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|
| EEF3UM | Automatic | Vinyl | Four | Z | B |
| EBV2LA | Automatic | Vinyl | Two | X | C |
| EGK6P3 | Automatic | Vinyl | Four | Y | A |
| EZKZXD | Automatic | Vinyl | Two | Z | C |
| ED9BUV | Automatic | Vinyl | Two | Y | A |
| E9PUA6 | Manual | Cloth | Four | Z | B |
| EJZ6T8 | Manual | Vinyl | Four | X | B |
| EWEC56 | Manual | Vinyl | Four | Z | A |
| EP3ARK | Automatic | Vinyl | Four | Y | C |
| EZ3K2B | Manual | Vinyl | Four | X | A |

License plate: EZKZXD
Which class, A, B, or C, does this vehicle belong to?
Reply with only ANSWER: followed by A, B, or C.
```
