# Monaa-Lisa
Softwarepraktikum von Basti, Nick, Lenio und Nico

## Quickstart (Development)

1. **Copy the example environment file:**
   ```sh
   cp .env.example .env
   # Edit .env and set your own DB user, password, and database name - This has to be set otherwise nothing will run.
   ```

2. **Start the development environment (VSCode Dev Container or Docker Compose):**
   - **VSCode Dev Container:**
     - Open the folder in VSCode and "Reopen in Container".
   - **Docker Compose (manual):**
     ```sh
     docker-compose up --build
     ```

3. **Access the app:**
   - Frontend: http://localhost:5173
   - Database: localhost:5432 (Postgres)

4. **Run SemanticPaper**
    - In the VSCode Remote Dev container move into the correct directory:
    ```sh
    cd /app/MonaaLisa/src
    ```
    - Then run the main.py (starts fetching Papers)
    ```sh
    python3 main.py
    ```

**Note:**
- You must have a valid `.env` file before starting!!
