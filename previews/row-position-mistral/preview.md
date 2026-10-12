# Row-position preview — no API calls

24 worlds × 2 record variants × 3 target rows × 2 response arms = 288 separate requests across 24 paired worlds. The first world's 12 exact requests appear below; preview.json contains all 288. Answer keys and headings are for inspection only.

## qf-list-000/record_1/row-05/direct

Expected C; pattern A; target row 5.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_1/row-01/direct

Expected C; pattern A; target row 1.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_2/row-05/direct

Expected B; pattern A; target row 5.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_1/row-05/visible

Expected C; pattern A; target row 5.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_2/row-10/visible

Expected B; pattern A; target row 10.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_2/row-10/direct

Expected B; pattern A; target row 10.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_2/row-01/direct

Expected B; pattern A; target row 1.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_2/row-05/visible

Expected B; pattern A; target row 5.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_2/row-01/visible

Expected B; pattern A; target row 1.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | B |
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_1/row-10/visible

Expected C; pattern A; target row 10.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_1/row-10/direct

Expected C; pattern A; target row 10.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_1/row-01/visible

Expected C; pattern A; target row 1.

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| UHHZ4N | Built for subzero temperatures | Manual | Vinyl | Two | Y | C |
| UHCVUS | Built for desert heat | Automatic | Vinyl | Four | X | C |
| UBRD8C | Equipped with snow tracks | Manual | Vinyl | Two | Z | A |
| UL7RZM | Operates on polar ice | Manual | Cloth | Two | X | A |
| UKZTG5 | Used at an equatorial station | Automatic | Cloth | Four | X | C |
| U8JPYQ | Designed for humid summers | Manual | Cloth | Two | Z | B |
| UBUX9A | Designed for frozen terrain | Automatic | Vinyl | Four | X | A |
| UV4MU5 | Equipped for hot sand | Automatic | Cloth | Four | Y | C |
| UV4BS7 | Operates in tropical forests | Manual | Vinyl | Four | Z | B |
| UVLNNP | Used at an Arctic station | Manual | Vinyl | Two | Y | A |

License plate: UHHZ4N
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```
