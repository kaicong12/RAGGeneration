# Application Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed:
- Node.js
- Yarn
- Python 3.8
- Virtualenv

If you don't have these installed, follow the steps below to install them.

## Application Setup

Once you have the prerequisites installed, follow these steps to set up the application:

1. **Clone the Repository**: If you haven't already, clone the repository to your local machine.

2. **Install JavaScript Dependencies**: Navigate to the root directory of the repository and run the following command to install the JavaScript dependencies:
   ```bash
   yarn
   ```

3. **Set Up Python Virtual Environment and Dependencies**:
   - Create a virtual environment:
     ```bash
     virtualenv env
     ```
   - Activate the virtual environment:
     ```bash
     source env/bin/activate
     ```
   - Install Python dependencies:
     ```bash
     pip install -r requirements.txt
     ```

4. **Change SQL Database Credentials**: modify the .env file in root and change the SQL database credentials

5. **Start the Application**: From the root of the repository, start the application using the following command:
   ```bash
   uvicorn main:app --reload
   ```

The application should now be running and accessible locally. The `--reload` flag enables auto-reloading of the server upon changes to the code, which is useful during development.

---
