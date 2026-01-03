Todo



# Acro_Scoring_Automation

Code to automate the scoring of Acro (https://www.acro-online.net).

## Definitions

- Range of number used in Acro: [min..max]
  - [1..3] means from 1 to 3 is possible
  - [01..10] means from 01 to 10 is possible and the number has leading zero
  - [001..999] means from 001 to 999 is possible and the number has leading zero

## Acro ctx File Information

- Path: <Acro_instalation_folder>/aerobatics/datax/<file_name>.ctx

The key information from the file used on the automation are below.

### Judges Information

- <judge[01..99]\_name1>Name
- <judge[01..99]\_name2>Surname

### Pilots Information

- <pilot[001..999]\_name1>Name
- <pilot[001..999]\_name2>Surname

### Sequences Information

- Sequence Details

  - <seq[01..99]\_active>A
    - List
      - A: Active
      - N: Not active [Check!]
  - <seq[01..99]\_level>ENT
  - <seq[01..99]\_title>Programme 1: Known Sequence
  - <seq[01..99]\_rpthdr>P1
  - <seq[01..99]\_type>Knwn
    - List
      - [Check!]

- Judges Details

  - <seq[01..99]\_fps>4
    - A single digit that represents:
      - 4 - Fair Play with Scoring CJ
      - 2 - Fair Play with Non-Scoring CJ
      - 3 - Raw Marks (CJ must be scoring)
  - <seq[01..99]\_judges>01AC02AJ03AJ 50AZ
    - Fixed positon - 14 possible judges plus the HZ column
      - [01..99]: Judge number - This maps how many judges scored the sequence and their respective numbers
      - AJ or AC or NC: Active Judge or Active Cheif Judge or Not scoring Cheif Judge
      - 50AZ or 50NZ or nothing (blank, not there):
        - If the Cheif Judge is scoring and it's Fair Play System (AC) then this block defines the HZ column: 50AZ
        - If the Cheif Judge is NOT scoring and it's Fair Play System (NC) then either this block is not there or it's 50NZ and the CJ column is used for HZ
        - If it's Raw Marks then CJ must score (AC)

- Pilots Details

  - <seq[01..99]\_flyorder>001002003
    - Fixed position
      - [001..999]: Pilot number - This maps the pilot numbers that flew this sequence
      - If the number starts with 5 (e.g. 501) then means the pilot is not in this sequence

- Scoring Details
  - <seq[01..99]\_knownkfacts>15 15 15 15 15 15 15 15 15 15
    - Fixed position - If the sequence is known (all pilots fly the same sequence) then this maps how many figures are in the sequence and their respective k-factors
      - 20 blocks (3 columns): A number (k factor) that uses 3 columns from 1 to 999 with spaces for padding after the number (e.g. 8 , 12 , 100)
  - <kseq[01..99]p[001..999]>12 315 412 315 412 620 530 722 830 712 4 -F
    - Fixed position - This is from another tag in the file but maps an individual sequence to a pilot and how many figures the sequence has and their respective k-factors
      - 20 blocks (4 columns): A number (k factor) that uses 3 columns from 1 to 999 with spaces for padding after the number (e.g. 8 , 12 , 100) followed by the figure letter or family number
      - Last 2 columns: A "-" or letter (version of the sequence) followed by a letter (U unknown, F for Free, K for Free Known, etc.)
  - <seq[01..99]\_oak[1..3]active>A
    - List - This shows the other possible scoring metrics
      - A: Active
      - N: Not active (not scored)
  - <seq[01..99]\_oak[1..3]title>Positioning
  - <seq[01..99]\_pen[01..10]active>A
    - List - This shows the possible penalties
      - A: Active
      - N: Not active (not scored)
  - <seq[01..99]\_pen[01..10]title>Too Low
  - <seq[01..99]\_pen[01..08]value>15
    - K factor
  - <seq[01..99]\_pen[09..10]rate>5
    - Rate per second of losing points with the score in seconds (how many seconds it was out side the box with -5 points/sec)

### Marks/Scoring Information

- <marks\_[01..99]p[001..999]J[01..99]>TnTnTnTnTnTnTnTnTnTn Tn 000000000
  - Fixed position
    - 20 blocks (2 columns): The score for each figure. This is a score per mark (sequence+pilot+judge). The possible values are:
      - Score number without the decimal place [00..95]
      - Tn for 10.0
      - AV for average
      - HZ for hard zero
      - PZ for perceived zero
      - Bk for blank (only applies to the CHZ column)
    - 3 blocks (2 columns): The 3 other possible scoring metrics (oak). This is a score per mark but always blank (Bk) for CHZ column.
      - Score number without the decimal place [00..95]
      - Tn for 10.0
      - AV for average [Check!]
    - 10 blocks (3 columns): The 10 possible penalties (pen). This is the same score for all judges in the same sequence and pilot (so it's repeated per mark but only one score for the entire sequence+pilot)
      - Integer [000..999]
      - The last 2 blocks (pen 9 and 10) are time penalties stored in seconds (e.g 003 for 3 seconds and 180 for 3 min)

## Architecture

## Solution Details

Acro ctx file >> Google Sheets >> Google Forms >> Google Sheets >> Acro ctx file