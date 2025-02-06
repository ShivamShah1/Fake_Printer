#!/usr/bin/env python3
import os
import sys
import time
import argparse
import pandas as pd
import asyncio
import aiohttp
import urllib3
import matplotlib.pyplot as plt

# Disable SSL warnings since we disable verification in aiohttp to avoid certificate errors.
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
        Synchronous printing of a layer (used in supervised mode).
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

        # Download the image synchronously (using requests is replaced in async mode).
        image_url = layer_data.get("image url", "")
        if image_url:
            image_path = os.path.join(layer_folder, f"layer_{layer_number}.png")
            try:
                # Using aiohttp for automatic mode; in supervised mode, you could use requests or similar.
                import requests
                r = requests.get(image_url, verify=False, timeout=10)
                r.raise_for_status()
                with open(image_path, "wb") as f:
                    f.write(r.content)
                print(f"Layer {layer_number} printed successfully.")
                self.successful_layers += 1
            except Exception as e:
                print(f"Error downloading image for layer {layer_number}: {e}")
                self.error_log.append(f"Layer {layer_number}: {e}")
                self.failed_layers += 1
        else:
            print(f"No image URL provided for layer {layer_number}.")
            print(f"Layer {layer_number} printed with data only.")
            self.successful_layers += 1

    async def print_layer_async(self, layer: pd.Series, session: aiohttp.ClientSession) -> tuple:
        """
        Asynchronously process a single layer:
         - Write layer data to disk.
         - Download the image (if provided) concurrently.
         - Check for inherent CSV errors.
        
        Returns:
            (layer_number, success_flag, error_message)
        """
        layer_number = layer.get("Layer Number", "unknown")
        layer_folder = os.path.join(self.output_folder, f"layer_{layer_number}")
        os.makedirs(layer_folder, exist_ok=True)

        # Write layer data to a file.
        layer_data_file = os.path.join(layer_folder, "layer_data.txt")
        try:
            with open(layer_data_file, "w") as f:
                f.write(layer.to_json(indent=2))
        except Exception as e:
            err_msg = f"Error writing layer data: {e}"
            return (layer_number, False, err_msg)

        inherent_error = False
        csv_error = layer.get("Error", "SUCCESS")
        if csv_error != "SUCCESS":
            # Log the inherent CSV error (but still attempt to process the layer).
            print(f"Layer {layer_number} CSV error: {csv_error}")
            inherent_error = True

        # Process image downloading if an image URL is provided.
        image_url = layer.get("image url", "")
        if image_url:
            image_path = os.path.join(layer_folder, f"layer_{layer_number}.png")
            try:
                # Set a timeout for the request.
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(image_url, ssl=False, timeout=timeout) as response:
                    response.raise_for_status()
                    content = await response.read()
                # Write the image to disk.
                with open(image_path, "wb") as f:
                    f.write(content)
            except Exception as e:
                err_msg = f"Error downloading image: {e}"
                return (layer_number, False, err_msg)
        else:
            print(f"No image URL provided for layer {layer_number}.")

        # If there was any inherent CSV error, mark the layer as a failure.
        if inherent_error:
            return (layer_number, False, f"Inherent CSV error: {csv_error}")
        return (layer_number, True, None)

    def supervised_mode(self) -> None:
        """
        Run FakePrinter in supervised mode.
        """
        for _, layer in self.csv_data.iterrows():
            layer_number = layer.get("Layer Number", "unknown")
            user_input = input(
                f"Press 'Enter' to print layer {layer_number} or type 'q' to quit: "
            ).strip().lower()
            if user_input == 'q':
                print("Printing aborted by user.")
                break

            if layer.get("Error", "SUCCESS") != "SUCCESS":
                print(f"Error detected in layer {layer_number}: {layer.get('Error')}")
                choice = input("Options: [i]gnore error and continue, [e]nd printing. (i/e): ").strip().lower()
                if choice == 'e':
                    print("Printing aborted by user due to error.")
                    break

            self.print_layer(layer)

    async def automatic_mode_async(self) -> None:
        """
        Run FakePrinter in automatic mode using asynchronous tasks to process layers concurrently.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.print_layer_async(layer, session)
                for _, layer in self.csv_data.iterrows()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        # Process the results from each async task.
        for layer_number, success, error in results:
            if success:
                self.successful_layers += 1
                print(f"Layer {layer_number} printed successfully.")
            else:
                self.failed_layers += 1
                self.error_log.append(f"Layer {layer_number}: {error}")
                print(f"Layer {layer_number} failed: {error}")

    def generate_summary(self) -> None:
        """
        Generate a summary of the print job.
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
            plt.axis('equal')  # Draw pie as a circle.
            chart_path = os.path.join(self.output_folder, "print_summary_chart.png")
            plt.savefig(chart_path)
            plt.close()
            print(f"Print summary chart saved to {chart_path}")
        except Exception as e:
            print(f"Error generating summary chart: {e}")

    def run(self, csv_file: str) -> None:
        """
        Run the FakePrinter process:
         - Load the CSV file.
         - Process layers in the specified mode.
         - Generate a summary.
        """
        self.load_csv_data(csv_file)

        if self.mode == "supervised":
            self.supervised_mode()
        elif self.mode == "automatic":
            # Run the asynchronous automatic mode.
            asyncio.run(self.automatic_mode_async())
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
