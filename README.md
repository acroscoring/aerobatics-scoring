Todo


# Acro_Scoring_Automation

Code to automate the scoring of Acro (https://www.acro-online.net).

## Definitions

- The ctx file uses a fixed positional and contant length structure
  - Each line starts with a tag delimited by "<" & ">"
  - The value is after the ">" (also fixed position and length)
  - There are 4 elements in each line
    - A "Table" followed by "ID" and "Column" and then the "Value" like <TableID_Column>Value

- For the selected tags below the format used to explain what they are is
  - Table and Column are as per what is in the ctx file
  - The ID range is represented with [min..max]
    - [1..3] means from 1 to 3 is possible
    - [01..10] means from 01 to 10 is possible and the number has leading zero
    - [001..999] means from 001 to 999 is possible and the number has leading zero
  - The Value shows what that Column means (what information it's holding) and some extra info if required


## Acro ctx File Information

- Path: <Acro_instalation_folder>/aerobatics/datax/<file_name>.ctx

The key information from the file used on the automation are below.

### Judges Information

- <judge[01..99]\_name1>Name
- <judge[01..99]\_name2>Surname

Example:
```
<judge01_name1>Pete
<judge01_name2>Mitchell
```

### Pilots Information

- <pilot[001..999]\_name1>Name
- <pilot[001..999]\_name2>Surname
- <pilot[001..999]\_lev1>Category
- <pilot[001..999]\_active>Status
    - A: Active
- <pilot[001..999]\_acreg>Aircraft Registration
- <pilot[001..999]\_actype>Aircraft Type

Example:
```
<pilot001_acreg>VH-TOP
<pilot001_active>A
<pilot001_actype>Extra 330SC
<pilot001_lev1>UNL
<pilot001_name1>Tom
<pilot001_name2>Kazansky
```

### Sequences Information

- Sequence Details

  - <seq[01..99]\_active>Status
    - A: Active
  - <seq[01..99]\_level>Category
  - <seq[01..99]\_title>Title Full
  - <seq[01..99]\_rpthdr>Title Summary
  - <seq[01..99]\_type>Type
  - <seq[01..99]\_lock>Locked
    - Y: It's locked and no modifications can be done
    - N: It's open and updates are allowed

- Judges Details

  - <seq[01..99]\_fps>Fair Play System
    - A single digit that represents:
      - 4 - Fair Play with Scoring CJ
      - 2 - Fair Play with Non-Scoring CJ
      - 3 - Raw Marks (CJ must be scoring)
  - <seq[01..99]\_judges>List of Judges
    - Fixed positon - 14 possible judges plus the HZ column
      - [01..99]: Judge number - This maps how many judges scored the sequence and their respective numbers
      - AJ or AC or NC: Active Judge or Active Cheif Judge or Not scoring Cheif Judge
      - 50AZ or 50NZ or nothing (blank, not there):
        - If the Cheif Judge is scoring and it's Fair Play System (AC) then this block defines the HZ column: 50AZ
        - If the Cheif Judge is NOT scoring and it's Fair Play System (NC) then either this block is not there or it's 50NZ and the CJ column is used for HZ
        - If it's Raw Marks then CJ must score (AC)

- Pilots Details

  - <seq[01..99]\_flyorder>Flying Order
    - Fixed position
      - [001..999]: Pilot number - This maps the pilot numbers that flew this sequence
      - If the number starts with 5 (e.g. 501) then means the pilot is not in this sequence

- Scoring Details
  - <seq[01..99]\_knownkfacts>K Factor
    - Fixed position - If the sequence is known (all pilots fly the same sequence) then this maps how many figures are in the sequence and their respective k-factors
      - 20 blocks (3 columns): A number (k factor) that uses 3 columns from 1 to 999 with spaces for padding after the number (e.g. 8 , 12 , 100)
  - <kseq[01..99]p[001..999]>K Factor
    - Fixed position - This is from another tag in the file but maps an individual sequence to a pilot and how many figures the sequence has and their respective k-factors
      - 20 blocks (4 columns): A number (k factor) that uses 3 columns from 1 to 999 with spaces for padding after the number (e.g. 8 , 12 , 100) followed by the figure letter or family number
      - Last 2 columns: A "-" or letter (version of the sequence) followed by a letter (U unknown, F for Free, K for Free Known, etc.)
  - <seq[01..99]\_oak[1..3]active>Overall K Factor Status
    - List - This shows the other possible scoring metrics
      - A: Active
      - N: Not active (not used/scored)
  - <seq[01..99]\_oak[1..3]title>Overall K Factor Title
  - <seq[01..99]\_pen[01..10]active>Penalty Status
    - List - This shows the possible penalties
      - A: Active
      - N: Not active (not scored)
  - <seq[01..99]\_pen[01..10]title>Penalty Title
  - <seq[01..99]\_pen[01..08]value>K Factor
  - <seq[01..99]\_pen[09..10]rate>Penalty Per Second Rate
    - Rate per second of losing points with the score in seconds (how many seconds it was out side the box with -5 points/sec)

Example:
```
<seq01_active>A
<seq01_flyorder>031030029
<seq01_fps>4
<seq01_judges>05AC06AJ07AJ08AJ                                        50AZ
<seq01_knownkfacts>7  8  10 17 14 3  5  10 
<seq01_level>ENT
<seq01_lock>Y
<seq01_oak1active>A
<seq01_oak1title>Positioning
<seq01_oak1value>5
<seq01_oak2active>N
<seq01_oak2title>
<seq01_oak2value>
<seq01_oak3active>N
<seq01_oak3title>
<seq01_oak3value>
<seq01_pen01active>N
<seq01_pen01title>Missed Slot
<seq01_pen01value>0
<seq01_pen02active>A
<seq01_pen02title>Safety Manoeuvres
<seq01_pen02value>10
<seq01_pen03active>A
<seq01_pen03title>Signalling Procedures
<seq01_pen03value>10
<seq01_pen04active>A
<seq01_pen04title>Too Low
<seq01_pen04value>100
<seq01_pen05active>N
<seq01_pen05title>Too High
<seq01_pen05value>0
<seq01_pen06active>A
<seq01_pen06title>Interruption
<seq01_pen06value>10
<seq01_pen07active>A
<seq01_pen07title>Insertion
<seq01_pen07value>10
<seq01_pen08active>A
<seq01_pen08title>Missed Roll Call
<seq01_pen08value>10
<seq01_pen09active>N
<seq01_pen09rate>
<seq01_pen09title>
<seq01_pen10active>N
<seq01_pen10rate>
<seq01_pen10title>
<seq01_rpthdr>P1 Known
<seq01_title>Programme 1: Known
<seq01_type>Knwn
```

### Marks/Scoring Information

Joins all together, it's a SeqID + p + pilotID + J + JudgeID

- <marks\_[01..99]p[001..999]J[01..99]>Scores
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
      - AV for average
    - 10 blocks (3 columns): The 10 possible penalties (pen). This is the same score for all judges in the same sequence and pilot (so it's repeated per mark but only one score for the entire sequence+pilot)
      - Integer [000..999]
      - The last 2 blocks (pen 9 and 10) are time penalties stored in seconds (e.g 003 for 3 seconds and 180 for 3 min)

Example:
```
<marks_01p031J07>90Tn80Tn75807080                        85       000000000   000000000      
<marks_01p031J08>9090808540709070                        80       000000000   000000000      
<marks_01p031J50>BkBkBkBkBkBkBkBk                        Bk       000000000   000000000      
<marks_02p029J05>HZ70808065808085                        80       000000000   000000001      
<marks_02p029J06>7075757085758085                        85       000000000   000000001      
<marks_02p029J07>HZ90709080Tn9095                        75       000000000   000000001      
<marks_02p029J08>HZ80757565458565                        70       000000000   000000001      
<marks_16p008J05>757585658065957075956575                95    000000000000000000000000      
<marks_16p008J06>707540505565756575857540                75    000000000000000000000000      
<marks_16p008J07>808060HZ8080Tn70609590HZ                80    000000000000000000000000      
<marks_16p008J08>707040506570856570808055                90    000000000000000000000000      
<marks_16p008J50>BkBkBkBkBkBkBkBkBkBkBkBk                Bk    000000000000000000000000      
```

## Architecture

## Solution Details

Acro ctx file >> Google Sheets >> Google Forms >> Google Sheets >> Acro ctx file