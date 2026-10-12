# Exact request sample; no model results

## order-new-023/v0/r3/before/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v1/r3/after/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v1/r3/both_left_near/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v0/r3/after/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v1/r3/after/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v0/r3/both_left_near/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v0/r3/after/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v1/r3/before/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v1/r3/both_right_near/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v0/r3/before/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v1/r3/before/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v1/r3/both_right_near/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v0/r3/both_left_near/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v1/r3/both_left_near/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | C |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## order-new-023/v0/r3/both_right_near/direct

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## order-new-023/v0/r3/both_right_near/visible

```text
These are records of previously observed vehicles. Every record is accurate. An individual vehicle's class is fixed, and its license plate identifies it. The audit marker is an administrative code assigned independently of class. MISSING means the verified class has not been recorded. If that cell is MISSING, make your best prediction from the other records.

| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |
|---|---|---|---|---|---|---|
| OC3VZE | Used at an equatorial station | Automatic | Cloth | Two | Z | B |
| O4E6F5 | Designed for humid summers | Manual | Vinyl | Two | Y | B |
| OFR9JX | Used at an Arctic station | Automatic | Vinyl | Four | X | A |
| OU29Y3 | Operates on polar ice | Manual | Vinyl | Two | Y | C |
| OJZWYB | Equipped for hot sand | Manual | Cloth | Two | X | A |
| O27KXY | Built for desert heat | Automatic | Cloth | Two | Z | B |
| OSESCR | Operates in tropical forests | Automatic | Cloth | Four | X | B |
| OCMBJ5 | Designed for frozen terrain | Manual | Vinyl | Two | Y | A |
| OJDB26 | Built for subzero temperatures | Manual | Cloth | Four | X | C |
| O5Y4JU | Equipped with snow tracks | Automatic | Vinyl | Two | Z | A |

License plate: OJZWYB
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```