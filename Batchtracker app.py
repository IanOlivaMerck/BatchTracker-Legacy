import tkinter as tk
from tkinter import filedialog
import time
import traceback
import OTIF_BT_APP_VERSIONpy

def write_to_textbox(message):
    """Write a message to the output textbox."""
    textbox.insert(tk.END, message + "\n")
    textbox.see(tk.END)
    root.update_idletasks()

def select_folder():
    """Open a folder selector and save the selected path."""
    selected_folder = filedialog.askdirectory(
        title="Select a folder"
    )

    if selected_folder:
        folder_path.set(selected_folder)

        write_to_textbox(
            f"Selected folder:\n{selected_folder}"
        )


def run_existing_code(folder):
    """
    Replace the code inside this function with your existing code.

    The selected folder is available through the variable:
        folder
    """

    # Example:
    # files = os.listdir(folder)
    # your_existing_function(folder)
    OTIF_BT_APP_VERSIONpy.run_batchtracker(folder)

'''
CODIGO PROPUESTO PARA BT QUE NOS DARIA EL ERROR EL TIEMPO QUE SE TARDO EN CORRER Y CUANDO SEA EXITOSO EL RUN, 
PROXIMAMENTE UNA LISTA DE ARCHIVOS PROCESADOS
'''
def run_batchtracker():

    """
    Display the selected folder, run the existing code,
    and report the execution time or error.
    """

    # Get the path from the StringVar
    selected_folder = folder_path.get()

    if not selected_folder:
        write_to_textbox("Error: Please select a folder first.")
        return

    # Show the selected address in the textbox
    write_to_textbox(
        f"Folder path:\n{selected_folder}"
    )

    write_to_textbox("Starting process...")

    start_time = time.perf_counter()

    try:
        # Run your existing code here
        run_existing_code(selected_folder)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        minutos, segundos = divmod(total_time, 60)
        write_to_textbox("Batchtracker is cooked")
        write_to_textbox(f"Tiempo total de ejecución: "f"{int(minutos)} minutos y {segundos:.2f} segundos")

    except Exception:
        end_time = time.perf_counter()
        total_time = end_time - start_time

        write_to_textbox(
            f"Process failed after {total_time:.2f} seconds."
        )
        write_to_textbox(
            "Error report:"
        )

        # Print the complete error traceback in the textbox
        error_report = traceback.format_exc()
        write_to_textbox(error_report)

root = tk.Tk()  
root.geometry("600x400")
root.title("BATCHTRACKER 2.0")

title = tk.Label(root, text="BIENVENIDO A BATCHTRACKER 2.0", font=("Arial", 22),)
title.pack(padx=20, pady=20,fill="x", expand=False)

instructions = tk.Label(root, text="Seleccione un directorio y luego haga clic en 'correr batchtracker'", font=("Arial", 11))   
instructions.pack(padx=20, pady=10)

textbox = tk.Text(root, height=7, font=("Arial", 10))
textbox.pack(
    padx=10,
    pady=10,
    fill="x",
    expand=False
)


buttonframe = tk.Frame(root)
buttonframe.columnconfigure(0, weight=1)
buttonframe.columnconfigure(1, weight=1)
folder_path= tk.StringVar()
button1 = tk.Button(buttonframe, text="directorio", font=("Arial", 12), command=select_folder)
button1.grid(row=0, column=0, padx=5, pady=5, sticky="ew", )
# EN EL BOTON 2 SE AGREGARIA LA SIGUIENTE PARTE CUANDO SE COMBINE CON EL CODIGO DE BT     command=run_batchtracker

button2 = tk.Button(buttonframe, text="correr batchtracker", font=("Arial", 12),command=run_batchtracker)
button2.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
buttonframe.pack(padx=10, pady=10, fill="x")
selected_folder = folder_path.get()

root.mainloop()