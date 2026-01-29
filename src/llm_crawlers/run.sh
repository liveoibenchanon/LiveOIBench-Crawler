#!/bin/bash
# Script to run IOI restructuring scripts for years 2002-2022

echo "Starting IOI restructuring scripts for years 2002-2022"

# Loop through years 2002 to 2022
for year in $(seq 2002 2022); do
  echo "====================================================="
  echo "Running restructuring script for IOI $year"
  echo "====================================================="
  
  python src/llm_crawlers/IOI_${year}_restructure.py
  python src/llm_crawlers/IOI_${year}_restructure_old.py
  # Check if script executed successfully
  if [ $? -eq 0 ]; then
    echo "Successfully processed IOI $year"
  else
    echo "Error processing IOI $year"
  fi
  
  echo ""
done

echo "All restructuring scripts completed."