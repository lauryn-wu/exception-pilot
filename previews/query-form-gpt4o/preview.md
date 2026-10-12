# Query-form preview — no API calls

24 worlds × 2 variants × 2 queries × 3 arms = 288 independent calls. The first world's 12 exact requests appear below; preview.json contains all 288. Answer keys and headings are for inspection only. The filler is copied within the same response.

## qf-list-000/record_2/key/direct

Expected B; pattern A.

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

## qf-list-000/record_1/profile/visible

Expected C; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_1/key/direct

Expected C; pattern A.

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

## qf-list-000/record_2/key/filler

Expected B; pattern A.

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
First copy the following neutral paragraph exactly, without its delimiters. Do not add an explanation. Then put ANSWER: followed by A, B, or C alone on the final line.
<neutral_paragraph>
Along the quiet shore, small waves move over smooth stones and return toward open water. Morning light spreads slowly across the surface, revealing ripples that overlap and fade. Farther inland, branches sway above the path while fallen leaves rest between exposed roots. The air feels cool beneath the trees, and the ground remains soft from overnight rain. Beyond the next bend, low hills rise behind the meadow, their outlines softened by mist. Wild grasses lean together when the breeze passes, then settle into their earlier places. Near the stream, moss covers the shaded stones with uneven patches of deep green. Water gathers briefly in shallow pools before continuing around roots and beneath loose branches. Beyond the shaded bank, thin reeds grow close together where the water becomes still. Small circles spread across the surface whenever droplets fall from the overhanging leaves. Soon the ripples disappear, leaving the reflections of branches clear against the pale sky. There is no hurry in the movement of the clouds or the slow change of light. Occasional birdsong comes from somewhere beyond the clearing, then gives way to silence again. The path follows the stream for some distance before climbing toward the edge of the woods. From that higher ground, the shore becomes visible through gaps between the slender trunks. Sunlight now reaches the meadow, touching the tips of the grasses and the scattered flowers. Dew remains on the leaves where the shade has not yet lifted from the ground. The same breeze travels through the clearing and out across the water toward the distant hills. Its passage is visible only in the brief movement of leaves and the changing texture of ripples. Along the shore, the smooth stones remain where the small waves have left them. Nothing requires attention here beyond the ordinary sounds of water, branches, and the passing wind. The morning continues quietly as the mist thins and the horizon grows clearer.
</neutral_paragraph>
```

## qf-list-000/record_1/key/filler

Expected C; pattern A.

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
First copy the following neutral paragraph exactly, without its delimiters. Do not add an explanation. Then put ANSWER: followed by A, B, or C alone on the final line.
<neutral_paragraph>
Along the quiet shore, small waves move over smooth stones and return toward open water. Morning light spreads slowly across the surface, revealing ripples that overlap and fade. Farther inland, branches sway above the path while fallen leaves rest between exposed roots. The air feels cool beneath the trees, and the ground remains soft from overnight rain. Beyond the next bend, low hills rise behind the meadow, their outlines softened by mist. Wild grasses lean together when the breeze passes, then settle into their earlier places. Near the stream, moss covers the shaded stones with uneven patches of deep green. Water gathers briefly in shallow pools before continuing around roots and beneath loose branches. Beyond the shaded bank, thin reeds grow close together where the water becomes still. Small circles spread across the surface whenever droplets fall from the overhanging leaves. Soon the ripples disappear, leaving the reflections of branches clear against the pale sky. There is no hurry in the movement of the clouds or the slow change of light. Occasional birdsong comes from somewhere beyond the clearing, then gives way to silence again. The path follows the stream for some distance before climbing toward the edge of the woods. From that higher ground, the shore becomes visible through gaps between the slender trunks. Sunlight now reaches the meadow, touching the tips of the grasses and the scattered flowers. Dew remains on the leaves where the shade has not yet lifted from the ground. The same breeze travels through the clearing and out across the water toward the distant hills. Its passage is visible only in the brief movement of leaves and the changing texture of ripples. Along the shore, the smooth stones remain where the small waves have left them. Nothing requires attention here beyond the ordinary sounds of water, branches, and the passing wind. The morning continues quietly as the mist thins and the horizon grows clearer.
</neutral_paragraph>
```

## qf-list-000/record_2/profile/visible

Expected B; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

## qf-list-000/record_2/key/visible

Expected B; pattern A.

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

## qf-list-000/record_2/profile/direct

Expected B; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_1/profile/filler

Expected C; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
First copy the following neutral paragraph exactly, without its delimiters. Do not add an explanation. Then put ANSWER: followed by A, B, or C alone on the final line.
<neutral_paragraph>
Along the quiet shore, small waves move over smooth stones and return toward open water. Morning light spreads slowly across the surface, revealing ripples that overlap and fade. Farther inland, branches sway above the path while fallen leaves rest between exposed roots. The air feels cool beneath the trees, and the ground remains soft from overnight rain. Beyond the next bend, low hills rise behind the meadow, their outlines softened by mist. Wild grasses lean together when the breeze passes, then settle into their earlier places. Near the stream, moss covers the shaded stones with uneven patches of deep green. Water gathers briefly in shallow pools before continuing around roots and beneath loose branches. Beyond the shaded bank, thin reeds grow close together where the water becomes still. Small circles spread across the surface whenever droplets fall from the overhanging leaves. Soon the ripples disappear, leaving the reflections of branches clear against the pale sky. There is no hurry in the movement of the clouds or the slow change of light. Occasional birdsong comes from somewhere beyond the clearing, then gives way to silence again. The path follows the stream for some distance before climbing toward the edge of the woods. From that higher ground, the shore becomes visible through gaps between the slender trunks. Sunlight now reaches the meadow, touching the tips of the grasses and the scattered flowers. Dew remains on the leaves where the shade has not yet lifted from the ground. The same breeze travels through the clearing and out across the water toward the distant hills. Its passage is visible only in the brief movement of leaves and the changing texture of ripples. Along the shore, the smooth stones remain where the small waves have left them. Nothing requires attention here beyond the ordinary sounds of water, branches, and the passing wind. The morning continues quietly as the mist thins and the horizon grows clearer.
</neutral_paragraph>
```

## qf-list-000/record_1/profile/direct

Expected C; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
Output only ANSWER: followed by A, B, or C.
```

## qf-list-000/record_2/profile/filler

Expected B; pattern A.

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
Description: Built for subzero temperatures
Transmission: Manual
Seat cover: Vinyl
Doors: Two
Which class, A, B, or C, does this vehicle belong to?
First copy the following neutral paragraph exactly, without its delimiters. Do not add an explanation. Then put ANSWER: followed by A, B, or C alone on the final line.
<neutral_paragraph>
Along the quiet shore, small waves move over smooth stones and return toward open water. Morning light spreads slowly across the surface, revealing ripples that overlap and fade. Farther inland, branches sway above the path while fallen leaves rest between exposed roots. The air feels cool beneath the trees, and the ground remains soft from overnight rain. Beyond the next bend, low hills rise behind the meadow, their outlines softened by mist. Wild grasses lean together when the breeze passes, then settle into their earlier places. Near the stream, moss covers the shaded stones with uneven patches of deep green. Water gathers briefly in shallow pools before continuing around roots and beneath loose branches. Beyond the shaded bank, thin reeds grow close together where the water becomes still. Small circles spread across the surface whenever droplets fall from the overhanging leaves. Soon the ripples disappear, leaving the reflections of branches clear against the pale sky. There is no hurry in the movement of the clouds or the slow change of light. Occasional birdsong comes from somewhere beyond the clearing, then gives way to silence again. The path follows the stream for some distance before climbing toward the edge of the woods. From that higher ground, the shore becomes visible through gaps between the slender trunks. Sunlight now reaches the meadow, touching the tips of the grasses and the scattered flowers. Dew remains on the leaves where the shade has not yet lifted from the ground. The same breeze travels through the clearing and out across the water toward the distant hills. Its passage is visible only in the brief movement of leaves and the changing texture of ripples. Along the shore, the smooth stones remain where the small waves have left them. Nothing requires attention here beyond the ordinary sounds of water, branches, and the passing wind. The morning continues quietly as the mist thins and the horizon grows clearer.
</neutral_paragraph>
```

## qf-list-000/record_1/key/visible

Expected C; pattern A.

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
