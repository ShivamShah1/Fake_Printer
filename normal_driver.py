#!/usr/bin/env python3
import os
import sys
import time
import argparse
import pandas as pd
import requests
import urllib3
import matplotlib.pyplot as plt

# Disable SSL warnings since we disable verification in requests to avoid certificate errors.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FakePrinter:
    def __init__(self, print_name: str, output_folder: str, mode: str) -> None:
        """
        Initialize the FakePrinter with a print name, output folder, and operating mode.
        """
        self.print_name = print_name
        self.output_folder = output_folder
        self.mode = mode.lower()
        self.csv_data = None
        self.total_layers = 0
        self.successful_layers = 0
        self.failed_layers = 0
        self.error_log = []

        # Create the output folder if it doesn't exist.
        os.makedirs(self.output_folder, exist_ok=True)

    def load_csv_data(self, csv_file: str) -> None:
        """
        Load the CSV data into a Pandas DataFrame.
        
        Pandas is chosen for its ability to easily read and manipulate CSV files.
        """
        try:
            self.csv_data = pd.read_csv(csv_file)
            self.total_layers = len(self.csv_data)
            print(f"Loaded {self.total_layers} layers from {csv_file}")
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            sys.exit(1)

    def print_layer(self, layer_data: pd.Series) -> None:
        """
        Simulate printing a layer:
         - Creates a dedicated folder for the layer.
         - Writes the layer’s data to a text file.
         - Downloads an associated image (if an image URL is provided).

        Requests is used for downloading images because it handles HTTP requests more robustly and
        easily allows us to disable SSL verification (to avoid certificate errors).
        """
        layer_number = layer_data.get("Layer Number", "unknown")
        layer_folder = os.path.join(self.output_folder, f"layer_{layer_number}")
        os.makedirs(layer_folder, exist_ok=True)

        # Save layer data to a text file.
        layer_data_file = os.path.join(layer_folder, "layer_data.txt")
        try:
            with open(layer_data_file, "w") as f:
                f.write(layer_data.to_json(indent=2))
        except Exception as e:
            print(f"Error writing layer data for layer {layer_number}: {e}")
            self.error_log.append(f"Layer {layer_number}: Error writing data: {e}")
            self.failed_layers += 1
            return

        # Download the image if an 'image url' is provided.
        image_url = layer_data.get("image url", "")
        if image_url:
            image_path = os.path.join(layer_folder, f"layer_{layer_number}.png")
            try:
                response = requests.get(image_url, verify=False, timeout=10)
                response.raise_for_status()  # Raise an error for bad HTTP responses.
                with open(image_path, "wb") as f:
                    f.write(response.content)
                print(f"Layer {layer_number} printed successfully.")
                self.successful_layers += 1
            except requests.RequestException as e:
                # The certificate verification error is avoided by verify=False.
                print(f"Error downloading image for layer {layer_number}: {e}")
                self.error_log.append(f"Layer {layer_number}: {e}")
                self.failed_layers += 1
        else:
            print(f"No image URL provided for layer {layer_number}. Skipping image download.")
            print(f"Layer {layer_number} printed with data only.")
            self.successful_layers += 1

    def supervised_mode(self) -> None:
        """
        Run FakePrinter in supervised mode.
        
        For each layer:
         - Wait for the user to press 'Enter' (or type 'q' to quit).
         - If an error is detected in the layer (based on the 'Error' column), prompt the user to either ignore the error or end printing.
        """
        for _, layer in self.csv_data.iterrows():
            layer_number = layer.get("Layer Number", "unknown")
            user_input = input(f"Press 'Enter' to print layer {layer_number} or type 'q' to quit: ").strip().lower()
            if user_input == 'q':
                print("Printing aborted by user.")
                break

            # Check for errors in the layer (the CSV column is expected to be 'Error').
            if layer.get("Error", "SUCCESS") != "SUCCESS":
                print(f"Error detected in layer {layer_number}: {layer.get('Error')}")
                choice = input("Options: [i]gnore error and continue, [e]nd printing. Enter choice (i/e): ").strip().lower()
                if choice == 'e':
                    print("Printing aborted by user due to error.")
                    break

            self.print_layer(layer)

    def automatic_mode(self) -> None:
        """
        Run FakePrinter in automatic mode.
        
        In this mode, all layers are processed sequentially without user intervention. Any errors are logged.
        """
        for _, layer in self.csv_data.iterrows():
            layer_number = layer.get("Layer Number", "unknown")
            if layer.get("Error", "SUCCESS") != "SUCCESS":
                print(f"Error detected in layer {layer_number}: {layer.get('Error')}. Logging error and continuing.")
                self.error_log.append(f"Layer {layer_number}: {layer.get('Error')}")
                self.failed_layers += 1
            else:
                self.print_layer(layer)
            # Simulate a delay to mimic printing (adjust as needed).
            time.sleep(0.5)

    def generate_summary(self) -> None:
        """
        Generate a summary of the print job.
        
        The summary includes:
         - A text file with print statistics and error logs.
         - A pie chart visualization of successful vs. failed layers (using Matplotlib).
        """
        summary = {
            "Print Name": self.print_name,
            "Total Layers": self.total_layers,
            "Successful Layers": self.successful_layers,
            "Failed Layers": self.failed_layers,
            "Errors": self.error_log
        }

        # Write the summary to a text file.
        summary_file = os.path.join(self.output_folder, "print_summary.txt")
        try:
            with open(summary_file, "w") as f:
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
            print(f"Print summary saved to {summary_file}")
        except Exception as e:
            print(f"Error writing summary file: {e}")

        # Create a pie chart summarizing the print job.
        try:
            labels = ['Successful Layers', 'Failed Layers']
            sizes = [self.successful_layers, self.failed_layers]
            colors = ['#4CAF50', '#F44336']
            plt.figure(figsize=(6, 6))
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            plt.title('Print Job Summary')
            plt.axis('equal')  # Ensure the pie is drawn as a circle.
            chart_path = os.path.join(self.output_folder, "print_summary_chart.png")
            plt.savefig(chart_path)
            plt.close()
            print(f"Print summary chart saved to {chart_path}")
        except Exception as e:
            print(f"Error generating summary chart: {e}")

    def run(self, csv_file: str) -> None:
        """
        Execute the FakePrinter process:
         - Loads the CSV file.
         - Runs the printing process in the specified mode.
         - Generates a summary at the end.
        """
        self.load_csv_data(csv_file)
        if self.mode == "supervised":
            self.supervised_mode()
        elif self.mode == "automatic":
            self.automatic_mode()
        else:
            print("Invalid mode selected. Please choose 'supervised' or 'automatic'.")
            sys.exit(1)

        self.generate_summary()

def parse_arguments() -> argparse.Namespace:
    """
    Parse and return command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="FakePrinter - Simulate printing layers from CSV data."
    )
    parser.add_argument("print_name", type=str, help="Name of the print job")
    parser.add_argument("output_folder", type=str, help="Destination output folder")
    parser.add_argument("mode", type=str, choices=["supervised", "automatic"],
                        help="Mode to run: 'supervised' or 'automatic'")
    parser.add_argument("csv_file", type=str, help="Path to the CSV file containing print layer data")
    return parser.parse_args()

def main() -> None:
    """
    Main function to execute FakePrinter.
    """
    args = parse_arguments()
    printer = FakePrinter(args.print_name, args.output_folder, args.mode)
    printer.run(args.csv_file)

if __name__ == "__main__":
    main()
