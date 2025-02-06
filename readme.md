# FakePrinter

FakePrinter is a simulation tool designed to process a large number of print layers (up to 2,000,000) from CSV data. It is optimized for both high-performance machines and resource-constrained devices (e.g., Raspberry Pi CM4) and supports two operation modes:

- **Supervised Mode:** Provides interactive, user-controlled processing with real-time prefetching.
- **Automatic Mode:** Leverages asynchronous execution to process layers concurrently for maximum throughput.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture and Optimization Details](#architecture-and-optimization-details)
  - [Supervised Mode](#supervised-mode)
  - [Automatic Mode](#automatic-mode)
- [Scope for Future Improvements](#scope-for-future-improvements)

---

## Overview

FakePrinter simulates a printing process where each layer (with its associated metadata and image) is processed based on CSV input. The tool is designed to work efficiently in two different modes:

- **Supervised Mode:** Users step through each layer manually. The system prefetches the current and several upcoming layers asynchronously, keeping an in-memory cache (capped at 10 items) to provide immediate feedback upon user interaction.
  
- **Automatic Mode:** All layers are processed concurrently using asynchronous execution. This dramatically reduces the overall runtime by processing multiple image downloads and data writes in parallel.

---

## Features

- **Dual Operation Modes:**  
  - *Supervised Mode:* Interactive, with asynchronous prefetching to minimize latency.
  - *Automatic Mode:* Fully asynchronous processing for rapid execution.
- **Optimized Resource Usage:**  
  - **Supervised Mode:** Implements an in-memory prefetch system that minimizes wait times, controls memory usage (capped at 10 items), and reduces unnecessary bandwidth consumption.
  - **Automatic Mode:** Uses Python’s `asyncio` and `aiohttp` libraries to perform concurrent operations, resulting in a significant speedup.
- **Error Handling and Logging:**  
  - Immediate error reporting in supervised mode with options to ignore or terminate.
  - Comprehensive logging of successes and failures.
- **Summary Generation:**  
  - Outputs a text-based summary and a pie chart visualization (via Matplotlib) of the print job's success and failure rates.

---

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ShivamShah1/Fake_Printer
   cd FakePrinter

```bash
pip install "numpy<2"
pip install pandas
pip install aiohttp
```

- Normal is normal code, it will only load the data when the user calls for it.
- Smart_driver is for async method which will call the data before the user ask for faster implementation of the process. This is the faster ways.
 
Usage
```bash
python3 normal_driver.py normal normal_folder automatic data.csv 
python3 smart_driver.py smart smart_folder supervised data.csv 
```

## Architecture and Optimization Details

### Supervised Mode

- **Speed Optimization:**
  - **Asynchronous Prefetching:**  
    As soon as the system starts, it asynchronously fetches the current layer plus the next five layers. When the user presses Enter, the result is immediately available from the in-memory cache.

- **Memory Optimization:**
  - **Capped In-Memory Store:**  
    The prefetching mechanism maintains a cache of up to 10 layers, preventing uncontrolled memory growth while ensuring that sufficient upcoming layers are preloaded.

- **Bandwidth Optimization:**
  - **Controlled Fetching:**  
    Only a limited number of image downloads are initiated concurrently, reducing network congestion and unnecessary bandwidth usage.

### Automatic Mode

- **Asynchronous Execution:**
  - **Concurrency:**  
    Uses `asyncio` and `aiohttp` to schedule all image downloads and data writes concurrently. This approach minimizes I/O blocking and reduces total processing time dramatically compared to a synchronous approach.

- **Efficiency:**
  - **Parallel Processing:**  
    By leveraging asynchronous tasks, the system processes hundreds (or even thousands) of layers concurrently, achieving near-optimal throughput.

### Scope for Future Improvements

- **Dynamic Prefetch Buffer:**  
  Implement a mechanism to dynamically adjust the prefetch buffer size based on runtime performance metrics (e.g., available memory, network speed).

- **Enhanced Error Recovery:**  
  Integrate exponential backoff and retry strategies for handling transient errors (e.g., network timeouts) during image downloads.

- **User Interface:**  
  Develop a graphical user interface (GUI) for supervised mode to provide real-time visual feedback, progress tracking, and interactive error handling.
