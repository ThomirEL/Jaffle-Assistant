# Jaffle Assistant

This repository contains a project for the **Jaffle Shop** dataset stored in a DuckDB database. The goal of the project is to integrate an agent for users to ask business questions to the agent and to get answers in natural language.

## Setup

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Project Structure

```
Jaffle-Assistant/
│
├── jaffle_shop.duckdb
├── data_exploration.ipynb
├── requirements.txt
└── README.md
```

### `jaffle_shop.duckdb`

This is the DuckDB database file containing the **Jaffle Shop dataset**.  
The database stores multiple relational tables representing the business data of the fictional Jaffle Shop.

Typical tables in the dataset include entities such as:

- customers
- orders
- products
- payments

### `data_exploration.ipynb`

This Jupyter notebook performs an initial exploration of the `jaffle_shop.duckdb` database.

The notebook includes code that:

- Connects to the DuckDB database
- Lists available tables
- Displays schema information for each table
- Shows the first 5 rows of each table

Running the notebook cell-by-cell provides a quick overview of:

- table structures
- column data types
- example records
- how the dataset is organized

This notebook is intended as a **starting point for understanding the dataset before building further analyses or applications**.

## Usage

1. Install dependencies
2. Open the notebook
3. Run the cells sequentially to explore the database
