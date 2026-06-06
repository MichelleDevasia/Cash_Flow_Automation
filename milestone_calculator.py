"""
Milestone Calculator - Independent Two-Stage Calculation

This module provides a clear implementation of the milestone value calculation
that keeps the two stages (Milestone Formation and Invoice Matching) completely separate.
"""


def calculate_milestone_value(
    milestone_percentage,
    sales_values,
    work_distribution_percentages
):
    """
    Calculate milestone value using independent two-stage logic.
    
    Args:
        milestone_percentage (float): Milestone % (e.g., 50.0)
        sales_values (list): Sales values from Milestone Formation stage
                           Example: [34.77, 0.11] (Act 1 sales, Act 3 sales)
        work_distribution_percentages (list): Work Distribution % from Invoice Matching stage
                                             Example: [50.0, 50.0] (Act 2 work%, Act 4 work%)
    
    Returns:
        float: Calculated milestone value
        
    Formula:
        Milestone% × [(Sales₁ × WorkDist%₁) + (Sales₂ × WorkDist%₂) + ... + (Salesₙ × WorkDistₙ%)]
    
    Example:
        >>> # Milestone: 50%
        >>> # Selected activities (Formation): Act 1 ($34.77), Act 3 ($0.11)
        >>> # Matched activities (Matching): Act 2 (50%), Act 4 (50%)
        >>> calculate_milestone_value(50.0, [34.77, 0.11], [50.0, 50.0])
        >>> # Result: 50% × [(34.77 × 50%) + (0.11 × 50%)]
        >>> #       = 50% × [17.385 + 0.055]
        >>> #       = 50% × 17.44
        >>> #       = 8.72
    """
    
    if not sales_values or not work_distribution_percentages:
        return 0.0
    
    # Pair items up to the max length of both lists.
    # If one list is shorter, reuse its last element.
    max_len = max(len(sales_values), len(work_distribution_percentages))
    
    # Calculate sum of (Sales × Work Distribution %) pairs
    activities_contribution = 0.0
    for i in range(max_len):
        sales = sales_values[i] if i < len(sales_values) else sales_values[-1]
        work_dist_pct = work_distribution_percentages[i] if i < len(work_distribution_percentages) else work_distribution_percentages[-1]
        
        # Individual contribution: Sales × (Work Distribution % / 100)
        contribution = sales * (work_dist_pct / 100)
        activities_contribution += contribution
    
    # Apply milestone percentage
    milestone_value = (milestone_percentage / 100) * activities_contribution
    
    return milestone_value


def calculate_milestone_value_with_details(
    milestone_percentage,
    sales_values,
    work_distribution_percentages,
    sales_labels=None,
    work_labels=None
):
    """
    Calculate milestone value and return detailed breakdown.
    
    Args:
        milestone_percentage (float): Milestone % (e.g., 50.0)
        sales_values (list): Sales values from Milestone Formation
        work_distribution_percentages (list): Work Distribution % from Invoice Matching
        sales_labels (list, optional): Labels for sales values (e.g., ["Act 1", "Act 3"])
        work_labels (list, optional): Labels for work distribution (e.g., ["Act 2", "Act 4"])
    
    Returns:
        dict: Dictionary containing:
            - 'milestone_value': Final calculated value
            - 'details': List of individual contributions with labels
            - 'formula': String representation of the calculation
            - 'breakdown': Step-by-step breakdown
    
    Example:
        >>> result = calculate_milestone_value_with_details(
        ...     50.0,
        ...     [34.77, 0.11],
        ...     [50.0, 50.0],
        ...     sales_labels=["Act 1", "Act 3"],
        ...     work_labels=["Act 2", "Act 4"]
        ... )
    """
    
    if not sales_values or not work_distribution_percentages:
        return {
            'milestone_value': 0.0,
            'details': [],
            'formula': 'No data provided',
            'breakdown': []
        }
    
    # Pair items up to the max length of both lists.
    # If one list is shorter, reuse its last element.
    max_len = max(len(sales_values), len(work_distribution_percentages))
    
    # Generate default labels if not provided
    if sales_labels is None:
        sales_labels = [f"Sales_{i+1}" for i in range(len(sales_values))]
    if work_labels is None:
        work_labels = [f"Work_Dist_{i+1}" for i in range(len(work_distribution_percentages))]
    
    # Calculate contributions
    details = []
    activities_contribution = 0.0
    
    for i in range(max_len):
        sales = sales_values[i] if i < len(sales_values) else sales_values[-1]
        work_dist_pct = work_distribution_percentages[i] if i < len(work_distribution_percentages) else work_distribution_percentages[-1]
        sales_label = sales_labels[i] if i < len(sales_labels) else sales_labels[-1]
        work_label = work_labels[i] if i < len(work_labels) else work_labels[-1]
        
        contribution = sales * (work_dist_pct / 100)
        activities_contribution += contribution
        
        details.append({
            'sales_label': sales_label,
            'sales_value': sales,
            'work_label': work_label,
            'work_dist_pct': work_dist_pct,
            'contribution': contribution,
            'formula': f"({sales} × {work_dist_pct}%) = {contribution}"
        })
    
    # Final calculation
    milestone_value = (milestone_percentage / 100) * activities_contribution
    
    # Build formula string
    contribution_formulas = " + ".join([
        f"({d['sales_value']} × {d['work_dist_pct']}%)" 
        for d in details
    ])
    formula_str = f"{milestone_percentage}% × [{contribution_formulas}] = {milestone_value}"
    
    # Build breakdown
    breakdown = [
        f"Milestone %: {milestone_percentage}%",
        f"Activities Contribution: {activities_contribution}",
        f"Final Value: ({milestone_percentage}/100) × {activities_contribution} = {milestone_value}"
    ]
    
    return {
        'milestone_value': milestone_value,
        'details': details,
        'formula': formula_str,
        'breakdown': breakdown
    }


if __name__ == "__main__":
    # Example 1: Simple calculation
    print("=" * 70)
    print("EXAMPLE 1: Hardware Milestone")
    print("=" * 70)
    
    result = calculate_milestone_value_with_details(
        milestone_percentage=15.0,
        sales_values=[34.77, 0.11],  # Act 1 sales, Act 3 sales
        work_distribution_percentages=[50.0, 50.0],  # Act 2 work%, Act 4 work%
        sales_labels=["Hardware-IT hardware (Act 1)", "Hardware/FAT (Act 3)"],
        work_labels=["Matched Act 2 (50%)", "Matched Act 4 (50%)"]
    )
    
    print(f"Milestone Value: ${result['milestone_value']:.2f}")
    print("\nBreakdown:")
    for line in result['breakdown']:
        print(f"  {line}")
    print("\nDetails:")
    for i, detail in enumerate(result['details'], 1):
        print(f"  Pair {i}:")
        print(f"    {detail['sales_label']}: ${detail['sales_value']}")
        print(f"    × {detail['work_label']}: {detail['work_dist_pct']}%")
        print(f"    = ${detail['contribution']:.2f}")
    
    print(f"\nFormula: {result['formula']}")
    
    # Example 2: Different scenario
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Software Milestone")
    print("=" * 70)
    
    result2 = calculate_milestone_value_with_details(
        milestone_percentage=30.0,
        sales_values=[5.16, 27.43],  # Software activities
        work_distribution_percentages=[75.0, 25.0],  # Different work distributions
        sales_labels=["Software 3rd Party", "Software SIEM/IDS/IAM"],
        work_labels=["Matched Activity 1", "Matched Activity 2"]
    )
    
    print(f"Milestone Value: ${result2['milestone_value']:.2f}")
    print("\nBreakdown:")
    for line in result2['breakdown']:
        print(f"  {line}")
    print("\nDetails:")
    for i, detail in enumerate(result2['details'], 1):
        print(f"  Pair {i}:")
        print(f"    {detail['sales_label']}: ${detail['sales_value']}")
        print(f"    × {detail['work_label']}: {detail['work_dist_pct']}%")
        print(f"    = ${detail['contribution']:.2f}")
    
    print(f"\nFormula: {result2['formula']}")
