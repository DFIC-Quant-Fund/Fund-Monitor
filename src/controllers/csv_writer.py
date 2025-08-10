# """
# CSV file management module for performance data.

# This module handles the persistence of performance metrics to CSV files.
# It is responsible for:
# - Writing performance results to CSV files
# - Managing existing data (appending, deduplication)
# - Ensuring data consistency in the CSV format

# This is a pure I/O module with no calculation logic.
# """

# import pandas as pd
# import os

# class PerformanceCSVWriter:
#     def __init__(self, fund, output_folder):
#         """
#         Initializes the CSV writer for performance data.
        
#         Args:
#             fund (str): The name of the fund
#             output_folder (str): Path to the output folder
#         """
#         self.fund = fund
#         self.output_folder = output_folder
#         self.output_file = os.path.join(output_folder, 'performance_returns.csv')

#     def save_results(self, results, date):
#         """
#         Saves the performance results to a CSV file.
        
#         Args:
#             results (dict): Dictionary of performance returns
#             date (datetime): The date for which the results were calculated
#         """
#         # Create a new dataframe to store the results
#         results_df = pd.DataFrame([results], index=[date])
#         results_df.index.name = "Date"

#         # Read existing data if the file exists and append new data
#         if os.path.exists(self.output_file):
#             saved_df = pd.read_csv(self.output_file, index_col="Date")
#             saved_df.index = pd.to_datetime(saved_df.index)
#             results_df = pd.concat([saved_df, results_df])

#         # Remove duplicates and sort
#         results_df = results_df[~results_df.index.duplicated(keep='last')]
#         results_df = results_df.sort_index()

#         # Save to CSV
#         results_df.to_csv(self.output_file, mode='w', index=True, header=True) 