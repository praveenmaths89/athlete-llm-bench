"""Draft probe questions for metric-to-column grounding in a wide VALD result table.
gold = the single correct column. ambiguous questions have gold=None and list the plausible columns.
Gold columns were decoded from the column names and must be confirmed by a domain expert before release."""
EXPLICIT = [
 ("the jump height computed from flight time, in inches", "Jump_Height_Flight_Time_in_Inches"),
 ("the jump height from the impulse-momentum method, in inches", "Jump_Height_Imp-Mom_in_Inches"),
 ("the jump height from the impulse-displacement method", "Jump_Height_Imp-Dis_"),
 ("the best-trial jump height from flight time", "Best_Jump_Height_Flight_Time_"),
 ("the mean over trials of the flight-time jump height", "Mean_Jump_Height_Flight_Time_"),
 ("the first-trial impulse-momentum jump height", "First_Jump_Height_Imp-Mom_"),
 ("the impulse-momentum jump height of the rebound jump", "Rebound_Jump_Height_Imp-Mom_"),
 ("peak power relative to body mass", "Peak_Power_/_BM"),
 ("concentric peak power per kilogram of body mass", "Concentric_Peak_Power_/_BM"),
 ("the best-trial peak power", "Best_Peak_Power"),
 ("the left-limb peak landing force", "Peak_Landing_Force_Left"),
 ("the left-right asymmetry of peak landing force", "Peak_Landing_Force_Asym"),
 ("RSI-modified calculated with the impulse-momentum jump height", "RSI-modified_Imp-Mom_"),
 ("the reactive strength index as jump height divided by contact time", "RSI_Jump_Height/Contact_Time_"),
 ("the mean over trials of contact time", "Mean_Contact_Time"),
 ("the best-trial active stiffness", "Best_Active_Stiffness"),
 ("eccentric braking rate of force development over the first 100 ms", "Eccentric_Braking_RFD-100ms"),
 ("eccentric braking impulse relative to body mass", "Eccentric_Braking_Impulse_/_BM"),
 ("the depth of the countermovement", "Countermovement_Depth"),
 ("the stiffness of the countermovement jump", "CMJ_Stiffness"),
 ("the flight time of the jump", "Flight_Time"),
 ("the contact time", "Contact_Time"),
 ("the right-limb eccentric braking impulse", "Eccentric_Braking_Impulse_Right"),
 ("the best-trial flight time", "Best_Flight_Time"),
]
UNDERSPECIFIED = [   # request, plausible columns (a good system flags ambiguity)
 ("jump height", ["Jump_Height_Imp-Mom_", "Jump_Height_Flight_Time_", "Jump_Height_Imp-Dis_"]),
 ("reactive strength index", ["RSI_Jump_Height/Contact_Time_", "RSI_Flight/Contact_Time_", "RSI-modified"]),
 ("peak power", ["Peak_Power", "Peak_Power_/_BM", "Concentric_Peak_Power", "Best_Peak_Power"]),
 ("stiffness", ["CMJ_Stiffness", "Active_Stiffness", "Landing_Stiffness"]),
]
