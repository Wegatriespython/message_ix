# Water-Austria Integration Project

## Project Overview

This project develops a reduced-form water-energy nexus model by integrating functional subsets of the MESSAGEix water module with the Austria energy system tutorial. The goal is to create a useful sandbox environment that preserves the full complexity and dynamics of water technologies while maintaining the manageable scope of a single-country model.

## Approach Philosophy

### Functional Subset Methodology

Rather than simplifying water module components, this project takes **exact functional subsets** from the water module and integrates them with Austria. This approach:

- **Preserves full complexity** of selected water technologies and constraints
- **Maintains exact behavior** of water-energy interactions
- **Focuses on dynamics** rather than data calibration or accuracy
- **Creates educational sandbox** for exploring water-energy nexus concepts

### Key Principles

1. **No Simplification**: Water technologies, constraints, and relationships are preserved exactly as implemented in the full water module
2. **Selective Integration**: Choose specific functional components that demonstrate key water-energy interactions
3. **Dynamic Focus**: Emphasize understanding system behavior and trade-offs rather than realistic data
4. **Incremental Development**: Build complexity through phases, starting with core interactions

## Technical Architecture

### Base Model: Austria Energy System

Starting point is the Austria tutorial energy model with:
- Single country (Austria) spatial scope
- Time horizon: 2010-2040 (10-year steps)
- Power plants: coal, gas, oil, bio, hydro, wind, solar
- End-use sectors: lighting and other electricity
- Standard MESSAGE framework structure

### Water Module Integration Strategy

#### Phase 1: Power Plant Cooling Integration
**Objective**: Demonstrate water-energy trade-offs in electricity generation

**Components to Extract**:
- Cooling technology framework from `water/build.py:cat_tec_cooling()`
- Cooling technology variants (ot_fresh, cl_fresh, air, ot_saline)
- Power plant cooling water requirements
- Cooling technology share constraints
- Basic water supply infrastructure

**Technologies**:
- Extend existing power plants: `{plant}__{cooling_type}`
- Water supply: `extract_surfacewater`
- Basic water availability constraints

**Key Dynamics**:
- Cooling efficiency vs. water consumption trade-offs
- Water availability constraints affecting power plant operation
- Technology choice under water scarcity scenarios

#### Phase 2: Water Supply Infrastructure
**Objective**: Add comprehensive water supply and demand management

**Components to Extract**:
- Water supply technologies from `water/data/water_supply.py`
- Urban/rural water infrastructure from `water/data/infrastructure.py`
- Basin-level water resource management
- Desalination technologies

**Technologies**:
- Multiple water sources (surface, ground, saline)
- Desalination options (membrane, distillation)
- Treatment and distribution infrastructure
- Water recycling and reuse

**Key Dynamics**:
- Water source diversification strategies
- Energy intensity of different water supply options
- Urban vs. industrial water allocation

#### Phase 3: Advanced Nexus Features
**Objective**: Explore complex water-energy-environment interactions

**Components to Extract**:
- Irrigation and agricultural water demands
- Environmental flow requirements
- Seasonal/temporal water variability
- Climate change impacts on water availability

**Key Dynamics**:
- Multi-sector water competition
- Climate adaptation strategies
- Long-term water-energy planning

## Implementation Strategy

### Development Approach

1. **Script-Based Implementation**: Build as Python scripts rather than notebooks for better modularity and reusability

2. **Modular Architecture**: 
   - `water_austria/build.py`: Core integration logic
   - `water_austria/data/`: Data preparation functions
   - `water_austria/config/`: Configuration files
   - `water_austria/scripts/`: Example usage scripts

3. **Exact Function Extraction**: Copy and adapt specific functions from water module with minimal modifications

4. **Fictional Enhancements**: Add fictional elements to Austria to better demonstrate water dynamics:
   - Coastal regions for desalination
   - Multiple river basins
   - Industrial water users
   - Urban water systems

### Technical Requirements

- Preserve exact water module data structures and parameter definitions
- Maintain compatibility with MESSAGEix Scenario API
- Use existing water module utility functions where possible
- Document all modifications and adaptations clearly

## Expected Outcomes

### Educational Value
- Demonstrate water-energy nexus concepts in familiar context
- Show impact of water constraints on energy system planning
- Illustrate trade-offs between water and energy technologies
- Provide sandbox for policy scenario testing

### Technical Contributions
- Modular water-energy integration framework
- Simplified entry point for water module functionality
- Testing ground for water module enhancements
- Reference implementation for other regional applications

## Project Structure

```
water_austria/
├── README.md                    # This file
├── build.py                     # Core integration functions
├── data/                        # Data preparation modules
│   ├── __init__.py
│   ├── cooling.py              # Power plant cooling data
│   ├── supply.py               # Water supply infrastructure
│   └── demands.py              # Water demand definitions
├── config/                      # Configuration files
│   ├── technology.yaml         # Water technology definitions
│   ├── set.yaml               # Set definitions
│   └── austria_water.yaml     # Austria-specific parameters
└── scripts/                    # Example usage scripts
    ├── phase1_cooling.py       # Phase 1 implementation
    ├── phase2_supply.py        # Phase 2 implementation
    └── examples/               # Usage examples
```

## Development Roadmap

### Immediate Goals
1. Establish project structure and documentation
2. Extract cooling technology framework (Phase 1)
3. Create Austria-water base scenario
4. Implement basic water supply constraints
5. Test cooling technology integration

### Short-term Goals
- Complete Phase 1 cooling integration
- Add fictional water infrastructure to Austria
- Create demonstration scripts
- Document water-energy trade-offs

### Medium-term Goals
- Implement Phase 2 water supply infrastructure
- Add desalination and treatment technologies
- Explore urban water systems
- Create policy scenario examples

### Long-term Vision
- Complete Phase 3 nexus features
- Seasonal/temporal dynamics
- Climate change scenarios
- Educational tutorial materials

## Notes

This project serves as both a technical integration exercise and an educational resource. The focus is on preserving the sophisticated dynamics of the water module while making them accessible in a simpler context. Success is measured by the clarity of water-energy interactions demonstrated, not by the realism of the underlying data.