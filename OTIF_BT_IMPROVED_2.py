## one time use imports
from getpass import getuser
from time import perf_counter
inicio = perf_counter()

# la funcion getuser() lee el nombre del usuario actual, tu muid
# si no quiere funcionar o esta dando el muid incorrecto elimina-
# getuser de dentro del parentesis de format y pon tu muid entre comillas
base_address = r"C:\Users\{0}\MerckGroup".format(getuser())
#esta es la variable que tienes que cambiar cada mes
# copia y pega el nombre de la carpeta del nuevo mes
# no quites las diagonales "\\" ya que las necesita el codigo
month="\\Noviembre 2026"
print(
    f"Usuario que actualizo Batch Tracker: {getuser()}",
    f"Month: {month}")

import pandas as pd
import glob
import os
from datetime import timedelta
import numpy as np
from pandas.tseries.offsets import BDay
# ## Auxiliar Functions
def clean_rows_based_on_prefix(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Cleans the DataFrame by removing rows where the specified column does not contain
    elements starting with 'M*', 'MX*', 'C*', or 'tbc'.
    Parameters:
    df (pd.DataFrame): The DataFrame to clean.
    column_name (str): The name of the column to check for prefixes.
    Returns:
    pd.DataFrame: The cleaned DataFrame with rows removed where the specified column
                  does not start with the specified prefixes."""
    # Define the prefixes to check
    prefixes = ('M', 'MX', 'C', 'tbc')
    # Create a mask for rows that start with the specified prefixes
    mask = df[column_name].str.startswith(prefixes, na=False)
    # Filter the DataFrame based on the mask
    cleaned_df = df[mask]
    return cleaned_df
def set_fin_column(df: pd.DataFrame, column_name_1: str, column_name_2: str) -> pd.DataFrame:
    """ Compares the specified columns in the DataFrame.
    Creates a new column 'FIN' which takes the value of 'column_name_1' if it is greater,
    otherwise takes the value of 'column_name_2'. If one of the columns is empty,
    it automatically selects the other one.
    Parameters:
    df (pd.DataFrame): The DataFrame to modify.
    column_name_1 (str): The name of the first column to compare.
    column_name_2 (str): The name of the second column to compare.
    Returns:
    pd.DataFrame: The modified DataFrame with the new 'FIN' column."""
    # Fill NaN values in the columns to avoid comparison issues
    df[column_name_1] = df[column_name_1].fillna(df[column_name_2])
    df[column_name_2] = df[column_name_2].fillna(df[column_name_1])
    # Create the 'FIN' column based on the comparison
    df['FIN'] = df[column_name_1].where( pd.to_datetime(df[column_name_1], errors='coerce') >  pd.to_datetime(df[column_name_2], errors='coerce'), df[column_name_2])
    return df
##### SÓLO SÓLIDOS Y TIROIDEOS #############
def merge_fabri_to_acondi(df_acondi, df_fabri, family,liberacion_granel):
    # Merge the two DataFrames on 'LOTE DE GRANEL'
    df_acondi["LOTE PT"]=df_acondi["LOTE PT"].apply(lambda x: x.strip())
    df_fabri["LOTE DE GRANEL"]=df_fabri["LOTE DE GRANEL"].apply(lambda x: x.strip())
    merged_df = df_acondi.merge(
        df_fabri[['LOTE DE GRANEL', 'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN',
                  'SKU', 'DESCRIPCIÓN', 'PR_ENTREGA EXPEDIENTE GR PLAN', liberacion_granel,
                   "GR_CANTIDAD", "GR_CANTIDAD C/YIELD","ORDEN GR","RECURSO GR" ]],
        on='LOTE DE GRANEL',
        how='outer'  # Use 'outer' to include all records from both DataFrames
    )
    merged_df["BT_analysis"]="Si va"
    claves_no_va=["MX11900221", "MX11900223", "MX11900077", "3185850012", "3184630003",
    "3184530004", "3184720003", "3186220002", "3194520015", "MX11900325",
    "MX11900483", "MX11900449", "3186280027", "3186280018", "3214230003",
    "3186280025","3184630002", "3186280029", "3186280030", "3185640022",
    "3185640021", "3951770115", "3951770114", "3951030071", "3951090007",
    "3951030070", "3951780112","3951090006" ]
    
    # Identify rows where SKU_x is missing
    missing_mask = merged_df["SKU_x"].isna() | (merged_df["SKU_x"] == "")
    # Replace SKU_x and DESCRIPCIÓN_x with values from _y
    merged_df.loc[missing_mask, "SKU_x"] = merged_df.loc[missing_mask, "SKU_y"]
    merged_df.loc[missing_mask, "DESCRIPCIÓN_x"] = merged_df.loc[missing_mask, "DESCRIPCIÓN_y"]
    # --- Case 1: family == "solids" ---
    if family == "solids":    
        condition = (
            merged_df["SKU_y"].isin(claves_no_va) &
            (merged_df["SKU_x"].isna() | (merged_df["SKU_x"].astype(str).str.strip() == "")))
        merged_df.loc[condition, "BT_analysis"] = "No va"
    # --- Case 2: family == "tyroids" ---
    elif family == "tyroids":
        # If description_y does not contain MMSA or BRA → "No va"
        invalid_desc_mask = ~merged_df["DESCRIPCIÓN_y"].str.contains("MMSA|BRA", na=False)
        merged_df.loc[missing_mask & invalid_desc_mask, "BT_analysis"] = "No va"       
    df_acondi_cosolidated=merged_df   
    df_acondi_cosolidated["LOTE DE GRANEL 2"]="No Aplica"
    df_acondi_cosolidated["TYPE_BATCH"]="E2E"
    def classify(row):
        if pd.notna(row['LOTE DE GRANEL']) and row['LOTE DE GRANEL'].startswith('MX'):
            return 'IMPORTED'
        return row['TYPE_BATCH'] 
    df_acondi_cosolidated["TYPE_BATCH"] = df_acondi_cosolidated.apply(classify, axis=1)
    df_acondi_cosolidated.rename(columns={'SKU_x':"SKU",'DESCRIPCIÓN_x':"DESCRIPCIÓN"},inplace=True)   
    return df_acondi_cosolidated

##### SÓLO LIQUIDOS #############
def merge_and_process_batches(df_acondi, df_fabri):
    # Match LOTE DE GRANEL with LOTE DE GRANEL in df_acondi
    df_acondi["LOTE PT"]=df_acondi["LOTE PT"].apply(lambda x: x.strip())
    df_fabri["LOTE DE GRANEL"]=df_fabri["LOTE DE GRANEL"].apply(lambda x: x.strip())
    #esta seccion seria la que se podria corregir o acortar
    merged_1 = df_acondi.merge(
        df_fabri[['LOTE DE GRANEL', 'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 
                   'ENTREGA ÓRDEN ANALÍTICA PLAN', 'PL_STATUS', 'PR_ENTREGA EXPEDIENTE GR PLAN',
                    "GR_CANTIDAD", "GR_CANTIDAD C/YIELD", "ORDEN GR", "RECURSO GR"]],
        left_on='LOTE DE GRANEL',
        right_on='LOTE DE GRANEL',
        how='left')
    # Rename columns with suffix _1
    merged_1 = merged_1.rename(columns={
        'FIN FABRI PLAN': 'FIN FABRI PLAN_1',
        'PR_ENTREGA MUESTRA PLAN': 'PR_ENTREGA MUESTRA PLAN_1',
        'ENTREGA ÓRDEN ANALÍTICA PLAN': 'ENTREGA ÓRDEN ANALÍTICA PLAN_1',
        'PL_STATUS': 'PL_STATUS_1',
        'PR_ENTREGA EXPEDIENTE GR PLAN': 'PR_ENTREGA EXPEDIENTE GR PLAN_1'})
    # Match LOTE DE GRANEL from df_fabri with LOTE DE GRANEL 2 in df_acondi
    merged_2 = merged_1.merge(
        df_fabri[['LOTE DE GRANEL', 'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 
                   'ENTREGA ÓRDEN ANALÍTICA PLAN', 'PL_STATUS', 'PR_ENTREGA EXPEDIENTE GR PLAN']],
        left_on='LOTE DE GRANEL 2',
        right_on='LOTE DE GRANEL',
        how='left')
    # Rename columns with suffix _2
    merged_2 = merged_2.rename(columns={
        'FIN FABRI PLAN': 'FIN FABRI PLAN_2',
        'PR_ENTREGA MUESTRA PLAN': 'PR_ENTREGA MUESTRA PLAN_2',
        'ENTREGA ÓRDEN ANALÍTICA PLAN': 'ENTREGA ÓRDEN ANALÍTICA PLAN_2',
        'PL_STATUS': 'PL_STATUS_2',
        'PR_ENTREGA EXPEDIENTE GR PLAN': 'PR_ENTREGA EXPEDIENTE GR PLAN_2',
        'LOTE DE GRANEL_x':'LOTE DE GRANEL'})
        
    # Compare the columns and create new columns with the most recent date
    # Update df_acondi with the new columns
    merged_2['FIN FABRI PLAN'] =                set_fin_column(df=merged_2,column_name_1='FIN FABRI PLAN_1',column_name_2='FIN FABRI PLAN_2')["FIN"]
    merged_2['PR_ENTREGA MUESTRA PLAN'] =       set_fin_column(df=merged_2,column_name_1='PR_ENTREGA MUESTRA PLAN_1',column_name_2='PR_ENTREGA MUESTRA PLAN_2')["FIN"]
    merged_2['ENTREGA ÓRDEN ANALÍTICA PLAN'] =  set_fin_column(df=merged_2,column_name_1='ENTREGA ÓRDEN ANALÍTICA PLAN_1',column_name_2='ENTREGA ÓRDEN ANALÍTICA PLAN_2')["FIN"]
    merged_2['PR_ENTREGA EXPEDIENTE GR PLAN'] = set_fin_column(df=merged_2,column_name_1='PR_ENTREGA EXPEDIENTE GR PLAN_1',column_name_2='PR_ENTREGA EXPEDIENTE GR PLAN_2')["FIN"]
    merged_2

    df_acondi_2=merged_2[['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'PL_STATUS_x' ,'FECHA REQ', 'FECHA OTIF','FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN',  
                          'PR_ENTREGA EXPEDIENTE GR PLAN','ENTREGA ÓRDEN ANALÍTICA PLAN','ACO_FIN ACONDI PLAN','PT_ENTREGA EXPEDIENTE PLAN','FECHA LIBERACION V0', "GR_CANTIDAD", 
                          "GR_CANTIDAD C/YIELD", "PT_CANTIDAD", "PT_CANTIDAD C/YIELD", "ORDEN GR", "ORDEN PT", "RECURSO PT", "RECURSO GR"]]
    df_acondi_2.rename(columns={'PL_STATUS_x':"PL_STATUS"})
    df_acondi_2["TYPE_BATCH"]="E2E"
    df_acondi_2["BT_analysis"]="Si va"
    return df_acondi_2, merged_2

def filter_by_date(df, year=None, months=None):
    # Ensure that the date columns are in datetime format
    df['FECHA LIBERACION V0'] = pd.to_datetime(df['FECHA LIBERACION V0'], errors='coerce')
    df['FIN FABRI PLAN'] = pd.to_datetime(df['FIN FABRI PLAN'], errors='coerce')
    # Filter by year
    if year is not None:
        df = df[(df['FECHA LIBERACION V0'].dt.year.isin(year)) | (df['FIN FABRI PLAN'].dt.year.isin(year))]
    # Filter by months
    if months is not None:
        df = df[(df['FECHA LIBERACION V0'].dt.month.isin(months)) | (df['FIN FABRI PLAN'].dt.month.isin(months))]
    return df  # Return only the specified columns

# Example usage
# filtered_df = filter_by_date(df_fabri, year=2023, months=[5, 6])  # Filter for May and June 2023
# filtered_df = filter_by_date(df_fabri, year=2023)  # Filter for the entire year 2023
# filtered_df = filter_by_date(df_fabri, months=[5, 6])  # Filter for May and June of any year
def update_lote_pt(bt_solidos, fabri_solidos):
    # Ensure the columns are named correctly
    bt_solidos = bt_solidos.copy()
    fabri_solidos = fabri_solidos.copy()
    # Iterate through the fabri_solidos DataFrame
    for index, row in fabri_solidos.iterrows():
        lote_granel_value    = row['Lote Granel']
        lote_value           = row['Lote']
        product_value        = row['Producto']
        fecha_dictamen_value = row['FECHA DE DICTAMEN']
        clave_value          = row['Clave']
        # Check if Lote Granel matches with LOTE DE GRANEL in BT_solidos
        matches = bt_solidos[bt_solidos['LOTE DE GRANEL'] == lote_granel_value]
        if not matches.empty:
            # Update the LOTE PT column in BT_solidos with the Lote value from fabri_solidos
            bt_solidos.loc[bt_solidos['LOTE DE GRANEL'] == lote_granel_value, 'LOTE PT'] = lote_value
            # Update the DESCRIPCIÓN column in BT_solidos with the PRODUCT value from fabri_solidos
            bt_solidos.loc[bt_solidos['LOTE DE GRANEL'] == lote_granel_value, 'DESCRIPCIÓN'] = product_value
            # Update the FECHA LIBERACION V0 column in BT_solidos with the FECHA DE DICTAMEN value from fabri_solidos
            bt_solidos.loc[bt_solidos['LOTE DE GRANEL'] == lote_granel_value, 'FECHA LIBERACION V0'] = fecha_dictamen_value
            bt_solidos.loc[bt_solidos['LOTE DE GRANEL'] == lote_granel_value, 'SKU'] = clave_value
    return bt_solidos

# Sample DataFrames (you would replace this with your actual DataFrames)
# merged_df = pd.DataFrame(...)  # Your merged DataFrame
# BatchTracker_df = pd.DataFrame(...)  # Your BatchTracker DataFrame

# Function to create Deviation_Info based on matches
# all deviation info functions should be just one. 
def create_deviation_info(row):
    deviation_info = []    
    # Check for matches in 'LOTE PT'
    if row['LOTE PT'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE PT']]
        for _, matched_row in matched_rows.iterrows():
            deviation_info.append(
                f"Lote PT: {matched_row['PR ID']} - {matched_row['Title']} \n"
                f"Due Date - Assigned to: {matched_row['Record State']} - {matched_row['HC Due Date']} - {matched_row['Assigned to']}\n"
                f"                                                                 "
            )
    # Check for matches in 'LOTE DE GRANEL'
    if row['LOTE DE GRANEL'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL']]
        for _, matched_row in matched_rows.iterrows():
            deviation_info.append(
                f"Lote GRANEL: {matched_row['PR ID']} - {matched_row['Title']} \n"
                f"Due Date - Assigned to: {matched_row['Record State']} - {matched_row['HC Due Date']} - {matched_row['Assigned to']}\n"
                f"                                                                 "
            )
    # Check for matches in 'LOTE DE GRANEL 2\n(Solo Liq. Esteriles)'
    if row['LOTE DE GRANEL 2'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL 2']]
        for _, matched_row in matched_rows.iterrows():
            deviation_info.append(
                f"Lote GRANEL 2 - LIQ: {matched_row['PR ID']} - {matched_row['Title']} \n"
                f"Due Date - Assigned to: {matched_row['Record State']} - {matched_row['HC Due Date']} - {matched_row['Assigned to']}\n"
                f"                                                                 "
            )
    return "\n".join(deviation_info) if deviation_info else ""

# Function to create Deviation Due Date based on matches
def create_deviation_due_date(row):
    due_dates = []
    # Check for matches in 'LOTE PT'
    if row['LOTE PT'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE PT']]
        due_dates.extend(matched_rows['HC Due Date'].dropna().tolist())
    # Check for matches in 'LOTE DE GRANEL'
    if row['LOTE DE GRANEL'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL']]
        due_dates.extend(matched_rows['HC Due Date'].dropna().tolist())
    # Check for matches in 'LOTE DE GRANEL 2\n(Solo Liq. Esteriles)'
    if row['LOTE DE GRANEL 2'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL 2']]
        due_dates.extend(matched_rows['HC Due Date'].dropna().tolist())
    # Filter the due_dates to ensure only valid dates are considered
    due_dates = [date for date in due_dates if isinstance(date, (pd.Timestamp, str)) and date != '']
    # If there are due dates, find the earliest one
    if due_dates:
        earliest_due_date = min(pd.to_datetime(due_dates, format="mixed", dayfirst=True, yearfirst=False))
        return earliest_due_date.strftime('%d/%m/%Y')  # Format the date as DD/MM/YYYY
    return ""

# Function to create Deviation Due Date based on matches
def create_deviation_closure_date(row,):
    due_dates = []
    # Check for matches in 'LOTE PT'
    if row['LOTE PT'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE PT']]
        due_dates.extend(matched_rows['Date Closed'].dropna().tolist())
    # Check for matches in 'LOTE DE GRANEL'
    if row['LOTE DE GRANEL'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL']]
        due_dates.extend(matched_rows['Date Closed'].dropna().tolist())
    # Check for matches in 'LOTE DE GRANEL 2\n(Solo Liq. Esteriles)'
    if row['LOTE DE GRANEL 2'] in merged_df['BatchNumberUnique'].values:
        matched_rows = merged_df[merged_df['BatchNumberUnique'] == row['LOTE DE GRANEL 2']]
        due_dates.extend(matched_rows['Date Closed'].dropna().tolist())
    # Filter the due_dates to ensure only valid dates are considered
    due_dates = [date for date in due_dates if isinstance(date, (pd.Timestamp, str)) and date != '']
    # If there are due dates, find the oldest one
    if due_dates:
        earliest_due_date = max(pd.to_datetime(due_dates, format="mixed", dayfirst=True, yearfirst=False))
        return earliest_due_date.strftime('%d/%m/%Y')  # Format the date as DD/MM/YYYY
    return ""

### Data Extraction from different sources
###################   BATCH TRACKER                 ######################################################################
path_BatchTracker= r"{0}\Seguimiento Servicio GMS P&G-BP - BATCHTRACKER\BASE BATCHTRACKER\Batch Tracker.xlsx".format(base_address)
BatchTracker_df= pd.read_excel(path_BatchTracker, header=1, sheet_name="BatchTracker")

####################   REVISORES ACONDI             ######################################################################
#ruta acondi es donde estan guardados los 3 documentos. 
ruta_acondi = r'{0}\EQ REVISORES - Equipo Revisor Acondicionamiento'.format(base_address)
# se prensta la opcion de tener 3 variables o un enunciado mas grande pero con menos variables
acondi_tiroideos_QA_piso  = pd.read_excel(r'{0}\Revisión Hormonales Ene 2023.xlsx'.format(ruta_acondi),sheet_name="Hormonales").copy()
acondi_liquidos_QA_piso   = pd.read_excel(r'{0}\Revisión Líquidos Ene 2023.xlsx'.format(ruta_acondi),  sheet_name="Líquidos").copy()
acondi_solidos_QA_piso = pd.read_excel(r'{0}\Revisión Sólidos Ene 2023.xlsx'.format(ruta_acondi),  sheet_name="Sólidos").copy()

acondi_tiroideos_QA_piso['ÁREA']="Tiroideos"
acondi_liquidos_QA_piso['ÁREA']="Líquidos"
acondi_solidos_QA_piso['ÁREA']="Sólidos"
#####################  REVISORES FABRI             #######################################################################
fabri_tiroideos_QA_piso  = pd.read_excel(r'{0}\RFT PRODUCCIÓN - Documents\RFT TIROIDEOS\Lista Ordenes EN PROCESO.xlsx'.format(base_address),sheet_name="OrdenesTiroideos").copy()
fabri_liquidos_QA_piso   = pd.read_excel(r'{0}\Expedientes fabricación - General\Lead Time.xlsx'.format(base_address),  sheet_name="Liquidos").copy()
fabri_solidos_QA_piso = pd.read_excel(r'{0}\RFT PRODUCCIÓN - Documents\RFT SOLIDOS\RFT SÓLIDOS.xlsm'.format(base_address),  sheet_name="Registro",header=4).copy()

fabri_tiroideos_QA_piso['ÁREA']="Tiroideos"
fabri_liquidos_QA_piso['ÁREA']="Líquidos"
fabri_solidos_QA_piso['ÁREA']="Sólidos"
###################    QC                            #########################################################################
QC_general  = pd.read_excel(r"{0}\Control de calidad Mexico - Monitoreo de liberaciones de PT 2022\Copy of MONITOREO DE LIBERACIONES PT 2022.xlsx".format(base_address)
                            ,sheet_name="BASE GENERAL 2022-2023").copy()
QC_tiroides  = pd.read_excel(r"{0}\LIBERACIONES EUTIROX - Documents\General\MONITOREO DE LIBERACIONES HORMONALES ENERO 2022.xlsx".format(base_address)
                            ,sheet_name="BASE GENERAL").copy()
############# QA Dictamen                      ################################################################################
#aqui van los planes de produccion, si se programa la interfaz esta es la unica carpeta que tendir que seleccionar los usuarios. 

directory            =r"{0}/Supply Chain - Planes de Producción 2026/{1}".format(base_address, month)
############## Programas de Planeacion         ################################################################################
# esta seccion requeire un poco de mas investigación para optimizar. es posible que lo mejor sea dejarlo asi aun que se optimice todo el documento. 
path_plan_liquidos =        glob.glob(os.path.join(directory, '*FABRICACIÓN-ACONDICIONAMIENTO LÍQUIDOS*.xlsx'))[0]
path_plan_solidos_fabri   = glob.glob(os.path.join(directory, '*PLAN FABRICACIÓN SOLIDOS*.xlsx'))[0] 
path_plan_solidos_acondi  = glob.glob(os.path.join(directory, '*PLAN ACONDICIONAMIENTO SOLIDOS*.xlsx'))[0]  
path_plan_tiroides_acondi = glob.glob(os.path.join(directory, '*PLAN ACONDICIONAMIENTO HORMONALES*.xlsx'))[0]
path_plan_tiroides_fabri  = glob.glob(os.path.join(directory, '*PLAN FABRICACIÓN HORMONALES*.xlsx'))[0] 
### Líquidos
plan_liquidos_fabri_NE=pd.read_excel(path_plan_liquidos, sheet_name="LIQUIDOS NE FABRI", header=3)
plan_liquidos_acondi_NE=pd.read_excel(path_plan_liquidos, sheet_name="LIQUIDOS NE EMPAQUE", header=4)
plan_liquidos_fabri_DC=pd.read_excel(path_plan_liquidos, sheet_name="DC fab", header=4)
plan_liquidos_acondi_DC=pd.read_excel(path_plan_liquidos, sheet_name="DC EMPAQUE", header=5)
plan_liquidos_fabri_AM=pd.read_excel(path_plan_liquidos, sheet_name="AMPOLLETAS FABRICACIÓN", header=4)
plan_liquidos_acondi_AM=pd.read_excel(path_plan_liquidos, sheet_name="AMPOLLETAS EMPAQUE", header=5)
### Sólidos
plan_solidos_fabri_TAB12= pd.read_excel(path_plan_solidos_fabri, sheet_name="TAB-12", header=5)
plan_solidos_fabri_TAB13= pd.read_excel(path_plan_solidos_fabri, sheet_name="TAB-13", header=4)
plan_solidos_fabri_TAB19= pd.read_excel(path_plan_solidos_fabri, sheet_name="TAB-19", header=5)
plan_solidos_fabri_TAB24= pd.read_excel(path_plan_solidos_fabri, sheet_name="TAB-24", header=5)
plan_solidos_fabri_ENV= pd.read_excel(path_plan_solidos_fabri, sheet_name="Envasado", header=4)
plan_solidos_fabri_PLV= pd.read_excel(path_plan_solidos_fabri, sheet_name="PLV", header=4)

plan_solidos_acondi_L3= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA 3", header=3)
plan_solidos_acondi_L4= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA 4", header=3)
plan_solidos_acondi_L5= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA 5", header=3)
plan_solidos_acondi_L7= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA 7", header=3)
plan_solidos_acondi_L6= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA 6 CAR-18", header=3)
plan_solidos_acondi_LC= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA CESOL", header=3)
plan_solidos_acondi_LM= pd.read_excel(path_plan_solidos_acondi, sheet_name="LINEA MANUAL", header=4)
### Tiroideos
plan_tiroideos_fabri_NF=pd.read_excel(path_plan_tiroides_fabri, sheet_name="NUEVA FORMULA", header=4)
plan_tiroideos_fabri_VF=pd.read_excel(path_plan_tiroides_fabri, sheet_name="Novotiral", header=4)
plan_tiroideos_acondi_L8=pd.read_excel(path_plan_tiroides_acondi, sheet_name="ASL8", header=5)
plan_tiroideos_acondi_L9=pd.read_excel(path_plan_tiroides_acondi, sheet_name="ASL9", header=5)
plan_tiroideos_acondi_L10=pd.read_excel(path_plan_tiroides_acondi, sheet_name="ASL10", header=5)
plan_tiroideos_acondi_LM=pd.read_excel(path_plan_tiroides_acondi, sheet_name="MAQUILA", header=3)
# ## Trackwise - Deviations
deviations_TW= pd.read_excel("PRODUCT_INFO.xlsx")
details_TW=pd.read_excel("DEVIATIONS_INFO.xlsx")
merged_df = pd.merge(deviations_TW, details_TW, left_on="PR ID", right_on="Record ID", how="left")
raw_crossdata= merged_df.to_excel("RawConsolidated.xlsx")

l_real_batches = []
for i in range(len(merged_df)):
    # Get the batch number, handling NaN values
    batch_number = merged_df["HC Batch Number"].iloc[i]    
    if pd.isna(batch_number):  # Check if the value is NaN
        real_batch = "MXXX"  # Set to "MXXX" if empty
    else:
        # Remove leading spaces and commas
        batch_number = batch_number.lstrip().replace(',', ' ')
        # Process the batch number
        if "MEX Lote" in batch_number:
            real_batch = batch_number.split(":")[-1]
        else: 
            real_batch = batch_number.split(" ")[0]
    l_real_batches.append(real_batch.replace(" ", ""))
merged_df["BatchNumberUnique"] = l_real_batches
merged_df = merged_df[['PR ID', 'Grid ID', 'HC Product Name', 'HC Item Code #',
       'HC Batch Number', 'HC Study Number', 'BatchNumberUnique', "Title", 'Record ID', 'Originator',
       'Date Opened', 'Date Closed', 'Assigned to',
       'Record State', 'HC Due Date']]
date_columns = ['Date Opened', 'Date Closed', 'HC Due Date']
# Convert the date column to datetime format
for i in date_columns:
    merged_df[i] = pd.to_datetime(merged_df[i], format="mixed", dayfirst=False, yearfirst=False)
    # Format the date to the desired format
    merged_df[i] = merged_df[i].dt.strftime('%d/%m/%Y')
# Save the DataFrame to an Excel file
merged_df.to_excel("consolidated_TW_report.xlsx", index=False)

# Apply the function to each row of BatchTracker_df and create the new column
BatchTracker_df['Deviation_Info'] = BatchTracker_df.apply(create_deviation_info, axis=1)

# Apply the function to each row of BatchTracker_df and create the new column 'Deviation Due Date'
BatchTracker_df['Deviation Due Date'] = BatchTracker_df.apply(create_deviation_due_date, axis=1)

# Display the updated BatchTracker_df
BatchTracker_df.to_excel("Deviations_BatchTracker.xlsx")
BatchTracker_df = BatchTracker_df

# ## Concatenación Revisores Fabri
# Select columns to concatenate 
columns_fabri_liquidos=      ['LOTE', 'PRODUCTO', 'FECHA DE FIN DE PROCESO','FECHA DE ENTREGA A DICTAMEN', 'Estatus']
columns_fabri_solidos=       ['Lote', 'Producto', 'Fecha fin de proceso','Fecha calidad',"Comentarios"]
columns_fabri_tiroideos=     ['Lote ','Producto','Fin  de Proceso','Fecha Entrega a\n QA','Estatus']
#Paso 1, integrar la nueva variable aquí
columns_batch_tracker_fabri= ['LOTE DE GRANEL','DESCRIPCIÓN', 'FIN FABRI REAL', 'PR_ENTREGA EXPEDIENTE GR REAL',"PR_Estatus"]
#cambio notable:diccionario
# Rename columns for each DataFrame
fabri_liquidos_QA_piso.rename(columns={
    'LOTE': 'LOTE DE GRANEL',
    'PRODUCTO': 'DESCRIPCIÓN',
    'FECHA DE FIN DE PROCESO': 'FIN FABRI REAL',
    'FECHA DE ENTREGA A DICTAMEN': 'PR_ENTREGA EXPEDIENTE GR REAL',
    'Estatus': 'PR_Estatus'
}, inplace=True)

fabri_solidos_QA_piso.rename(columns={
    'Lote': 'LOTE DE GRANEL',
    'Producto': 'DESCRIPCIÓN',
    'Fecha fin de proceso': 'FIN FABRI REAL',
    'Fecha calidad': 'PR_ENTREGA EXPEDIENTE GR REAL',
    'Comentarios': 'PR_Estatus'
}, inplace=True)

fabri_tiroideos_QA_piso.rename(columns={
    'Lotes ': 'LOTE DE GRANEL',
    'Producto': 'DESCRIPCIÓN',
    'Fin  de Proceso': 'FIN FABRI REAL',
    'Fecha Entrega a\n QA': 'PR_ENTREGA EXPEDIENTE GR REAL',
    'Estatus': 'PR_Estatus'
}, inplace=True)

# Concatenate the DataFrames
combined_Fabri_df = pd.concat([fabri_liquidos_QA_piso[columns_batch_tracker_fabri], fabri_solidos_QA_piso[columns_batch_tracker_fabri], fabri_tiroideos_QA_piso[columns_batch_tracker_fabri]], ignore_index=True)
combined_Fabri_df= combined_Fabri_df.dropna(subset=['LOTE DE GRANEL'])

# Ensure 'FIN FABRI REAL' is in datetime format
combined_Fabri_df['FIN FABRI REAL'] = pd.to_datetime(combined_Fabri_df['FIN FABRI REAL'], errors='coerce')

# Filter the DataFrame for dates in the year 2025
combined_Fabri_df = combined_Fabri_df[combined_Fabri_df['FIN FABRI REAL'] >"2024-11-01"]
combined_Fabri_df['LOTE DE GRANEL'] = combined_Fabri_df['LOTE DE GRANEL'].str.replace(' ', '', regex=True)

combined_Fabri_df.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\RV_Consolidated_Fabri_Review.xlsx".format(base_address), index=False)

# ## Concatenación Revisores Acondi
columns_acondi = [ 'LOTE PT', 'CLAVE', 'PRODUCTO','Fecha término de proceso MES','Entrega a Calidad']
columns_batch_tracker_acondi= ['LOTE PT','SKU', 'DESCRIPCIÓN', 'ACO_FIN ACONDI REAL', 'PT_ENTREGA EXPEDIENTE REAL']
#cambio notable: Diccionario
# Rename columns for each DataFrame
acondi_liquidos_QA_piso.rename(columns={
    'LOTE PT': 'LOTE PT',
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'Fecha término de proceso MES': 'ACO_FIN ACONDI REAL',
    'Entrega a Calidad': 'PT_ENTREGA EXPEDIENTE REAL'
}, inplace=True)

acondi_solidos_QA_piso.rename(columns={
    'LOTE PT': 'LOTE PT',
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'Fecha término de proceso MES': 'ACO_FIN ACONDI REAL',
    'Entrega a Calidad': 'PT_ENTREGA EXPEDIENTE REAL'
}, inplace=True)

acondi_tiroideos_QA_piso.rename(columns={
    'LOTE PT': 'LOTE PT',
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'Fecha término de proceso MES': 'ACO_FIN ACONDI REAL',
    'Entrega a Calidad': 'PT_ENTREGA EXPEDIENTE REAL'
}, inplace=True)

# Concatenate the DataFrames
combined_acondi_df = pd.concat([acondi_liquidos_QA_piso[columns_batch_tracker_acondi],
                                 acondi_solidos_QA_piso[columns_batch_tracker_acondi], 
                                 acondi_tiroideos_QA_piso[columns_batch_tracker_acondi]], ignore_index=True)

# Delete rows where 'LOTE PT' has NaN values
combined_acondi_df = combined_acondi_df.dropna(subset=['LOTE PT'])

# Ensure 'ACO_FIN ACONDI REAL' is in datetime format
combined_acondi_df['ACO_FIN ACONDI REAL'] = pd.to_datetime(combined_acondi_df['ACO_FIN ACONDI REAL'], errors='coerce')

# Optionally, filter for specific dates if needed (e.g., for the year 2025)
combined_acondi_df = combined_acondi_df[combined_acondi_df['ACO_FIN ACONDI REAL'] >"2024-11-01"]
combined_acondi_df['LOTE PT'] = combined_acondi_df['LOTE PT'].str.replace(' ', '', regex=True)

# Display the cleaned DataFrame
combined_acondi_df.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\RV_Consolidated_Acondi_Review.xlsx".format(base_address), index=False)
combined_acondi_df

# ## Concatenación QC
columns_qc_general   =      ['LOTE ','PRODUCTO O FAMILIA ','FECHA DE ENTRADA AL LABORATORIO', 'ENTREGA A DICTAMEN\n(mes/dia/año', 'ESTATUS\npara QC']
columns_qc_tiroideos =      [ 'LOTE ', 'PRODUCTO(Nombre de plan de muestreo)', 'FECHA DE ENTRADA AL LABORATORIO','ENTREGA A DICTAMEN\n(mes/dia/año', 'ESTATUS\npara QC' ]
columns_batch_tracker_QC=   [ 'LOTE' ,'DESCRIPCIÓN' ,'PR_ENTREGA MUESTRA REAL',  'ENTREGA ÓRDEN ANALÍTICA REAL', "QC_Estatus" ]
#cambio notable:diccionario
# Rename columns for each DataFrame
QC_general.rename(columns={
    'LOTE ': 'LOTE',
    'PRODUCTO O FAMILIA ': 'DESCRIPCIÓN',
    'FECHA DE ENTRADA AL LABORATORIO': 'PR_ENTREGA MUESTRA REAL',
    'ENTREGA A DICTAMEN\n(mes/dia/año': 'ENTREGA ÓRDEN ANALÍTICA REAL',
    'ESTATUS\npara QC': 'QC_Estatus'
}, inplace=True)
QC_tiroides.rename(columns={
    'LOTE ': 'LOTE',
    'PRODUCTO(Nombre de plan de muestreo)': 'DESCRIPCIÓN',
    'FECHA DE ENTRADA AL LABORATORIO': 'PR_ENTREGA MUESTRA REAL',
    'ENTREGA A DICTAMEN\n(mes/dia/año': 'ENTREGA ÓRDEN ANALÍTICA REAL',
    'ESTATUS\npara QC': 'QC_Estatus'
}, inplace=True)

# Concatenate the DataFrames
combined_qc_df = pd.concat([QC_general[columns_batch_tracker_QC], QC_tiroides[columns_batch_tracker_QC]], ignore_index=True)

# Delete rows where 'LOTE' has NaN values
combined_qc_df = combined_qc_df.dropna(subset=['LOTE'])

# Ensure 'PR_ENTREGA MUESTRA REAL' is in datetime format
combined_qc_df['PR_ENTREGA MUESTRA REAL'] = pd.to_datetime(combined_qc_df['PR_ENTREGA MUESTRA REAL'], errors='coerce')
combined_qc_df['ENTREGA ÓRDEN ANALÍTICA REAL'] = pd.to_datetime(combined_qc_df['ENTREGA ÓRDEN ANALÍTICA REAL'], errors='coerce')

# Filter the DataFrame for dates in the year 2025
combined_qc_df = combined_qc_df[combined_qc_df['PR_ENTREGA MUESTRA REAL'] >"2024-11-01"]
combined_qc_df['LOTE'] = combined_qc_df['LOTE'].str.replace(' ', '', regex=True)

# Display the filtered DataFrame
combined_qc_df.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\QC_Consolidated_QC.xlsx".format(base_address), index=False)

# ## Concatenación Planeación
# ### Tiroideos
#cambio notable: reduccion a variable
columns_tiroideos_fabri_NF=['Clave', 'Producto', 'Lote','Compresión',  'Muestras',  'Entrega de orden a QA','LIBERACION ANÁLISIS','Dictámen', 'CANTIDAD', 'Orden', 'TAB' ]
columns_tiroideos_fabri_VF=['Clave', 'Producto', 'Lote','Compresión',  'Muestras',  'Entrega de orden a QA','LIBERACION ANÁLISIS','Dictámen', 'CANTIDAD', 'Orden', 'TAB' ]

df_tiroideos_fabri_VF = clean_rows_based_on_prefix(plan_tiroideos_fabri_VF[columns_tiroideos_fabri_VF], 'Lote')
df_tiroideos_fabri_NF = clean_rows_based_on_prefix(plan_tiroideos_fabri_NF[columns_tiroideos_fabri_NF], 'Lote')

# Stack the data frames
df_fabri_tiroideos_consolidated = pd.concat([df_tiroideos_fabri_VF, df_tiroideos_fabri_NF], ignore_index=True)

# Create a mapping for renaming
rename_mapping = {
    'Clave': 'SKU',
    'Producto': 'DESCRIPCIÓN',
    'Lote': 'LOTE DE GRANEL',
    'Compresión': 'FIN FABRI PLAN',
    'Muestras': 'PR_ENTREGA MUESTRA PLAN',
    'Entrega de orden a QA': 'PR_ENTREGA EXPEDIENTE GR PLAN',
    'LIBERACION ANÁLISIS': 'ENTREGA ÓRDEN ANALÍTICA PLAN',
    'CANTIDAD': 'GR_CANTIDAD',
    "Orden": "ORDEN GR",
    "TAB": "RECURSO GR"}
# Rename the columns
df_fabri_tiroideos_consolidated.rename(columns=rename_mapping, inplace=True)
df_fabri_tiroideos_consolidated["PR_ENTREGA EXPEDIENTE GR PLAN"]= pd.to_datetime(df_fabri_tiroideos_consolidated["FIN FABRI PLAN"], errors="coerce")+ timedelta(days=7)
df_fabri_tiroideos_consolidated["GR_CANTIDAD C/YIELD"]= df_fabri_tiroideos_consolidated[["GR_CANTIDAD"]]
df_fabri_tiroideos_consolidated["LOTE DE GRANEL"]=df_fabri_tiroideos_consolidated["LOTE DE GRANEL"].apply(lambda x: x.strip())
df_fabri_tiroideos_consolidated.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Fabri_Tiroideos_Consolidated.xlsx".format(base_address), index=False)

# Save DataFrame to Excel file with table formatting
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Fabri_Tiroideos_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_fabri_tiroideos_consolidated.to_excel(writer, index=False, sheet_name='BT_Fabri_Tiroides_consolidates')  
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['BT_Fabri_Tiroides_consolidates']
    # Create a table
    num_rows, num_cols = df_fabri_tiroideos_consolidated.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Fabri_Tiroides', 'columns': [{'header': col} for col in df_fabri_tiroideos_consolidated.columns]})

columns_acondi_tiroideos_L10=['CLAVE', 'PRODUCTO',  'LOTE PT', 'LOTE GRANEL', 'Comentarios',  'FIN', 'LIBERACIÓN', 'Fecha de requerimiento','OTIF', 'CANTIDAD', 'Recurso', 'ORDEN']
columns_acondi_tiroideos_L9=['CLAVE', 'PRODUCTO',  'LOTE PT', 'LOTE GRANEL', 'Comentarios',  'FIN', 'LIBERACIÓN', 'Fecha de requerimiento','OTIF', 'CANTIDAD', 'Recurso', 'ORDEN']
columns_acondi_tiroideos_L8=['CLAVE', 'PRODUCTO',  'LOTE PT', 'LOTE GRANEL', 'Comentarios',  'FIN', 'LIBERACIÓN', 'Fecha de requerimiento','OTIF', 'CANTIDAD', 'Recurso', 'ORDEN']
columns_acondi_tiroideos_LM=['CLAVE', 'PRODUCTO',  'LOTE PT', 'LOTE GRANEL', 'Comentarios',  'Entrega', 'Fecha de requerimiento','LIBERACIÓN','OTIF', 'CANTIDAD','ORDEN']

df_tiroideos_acondi_L10 = clean_rows_based_on_prefix(plan_tiroideos_acondi_L10[columns_acondi_tiroideos_L10], 'LOTE PT')
df_tiroideos_acondi_L9  = clean_rows_based_on_prefix(plan_tiroideos_acondi_L9[columns_acondi_tiroideos_L9], 'LOTE PT')
df_tiroideos_acondi_L8  = clean_rows_based_on_prefix(plan_tiroideos_acondi_L8[columns_acondi_tiroideos_L8], 'LOTE PT')
df_tiroideos_acondi_LM  = clean_rows_based_on_prefix(plan_tiroideos_acondi_LM[columns_acondi_tiroideos_LM], 'LOTE PT')
df_tiroideos_acondi_LM["Recurso"]="MAQUILA"

# Stack the data frames
df_acondi_tiroideos_consolidated = pd.concat([df_tiroideos_acondi_L10, df_tiroideos_acondi_L9, df_tiroideos_acondi_L8], ignore_index=True)

# Create a mapping for renaming
#cambio notable: diccionario
rename_mapping = {
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'LOTE GRANEL': 'LOTE DE GRANEL',
    'LOTE PT': 'LOTE PT',
    'Comentarios': 'PL_STATUS',
    'FIN': 'ACO_FIN ACONDI PLAN',
    'LIBERACIÓN': 'FECHA LIBERACION V0',
    'Fecha de requerimiento': 'FECHA REQ',
    'OTIF':'FECHA OTIF', 
    'CANTIDAD': 'PT_CANTIDAD',
    "Recurso": "RECURSO PT",
    "ORDEN": "ORDEN PT"}
rename_mapping_maquila = {
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'LOTE GRANEL': 'LOTE DE GRANEL',
    'LOTE PT': 'LOTE PT',
    'Comentarios': 'PL_STATUS',
    'Entrega': 'ACO_FIN ACONDI PLAN',
    'LIBERACIÓN': 'FECHA LIBERACION V0',
    'Fecha de requerimiento': 'FECHA REQ',
    'OTIF':'FECHA OTIF', 
    'CANTIDAD': 'PT_CANTIDAD' ,
    "Recurso": "RECURSO PT",
    "ORDEN": "ORDEN PT"}

# Rename the columns
df_acondi_tiroideos_consolidated.rename(columns=rename_mapping, inplace=True)
df_tiroideos_acondi_LM.rename(columns=rename_mapping_maquila, inplace=True)
df_acondi_tiroideos_consolidated["PT_ENTREGA EXPEDIENTE PLAN"]= pd.to_datetime(df_acondi_tiroideos_consolidated["ACO_FIN ACONDI PLAN"], errors="coerce")+ timedelta(days=4)
final_columns_acondi_tiroideos = ['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'PL_STATUS',
 'ACO_FIN ACONDI PLAN', 'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF', 'PT_ENTREGA EXPEDIENTE PLAN', 'PT_CANTIDAD' , "RECURSO PT", "ORDEN PT"]

# Merge the two DataFrames on 'LOTE PT'
# Mergin dataframes to substitute dates for MAQUILA, new note: revisar compatibilidad con linea manual
df_acondi_tiroideos_consolidated_final = df_acondi_tiroideos_consolidated[final_columns_acondi_tiroideos].merge(
    df_tiroideos_acondi_LM[['LOTE PT', 'ACO_FIN ACONDI PLAN', 'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF']],
    on='LOTE PT',
    how='left',
    suffixes=('', '_y')  # This will help avoid confusion with column names
)

# Update the values in the original DataFrame based on the merged DataFrame
df_acondi_tiroideos_consolidated_final['ACO_FIN ACONDI PLAN'] = df_acondi_tiroideos_consolidated_final['ACO_FIN ACONDI PLAN_y'].combine_first(df_acondi_tiroideos_consolidated_final['ACO_FIN ACONDI PLAN'])
df_acondi_tiroideos_consolidated_final['FECHA LIBERACION V0'] = df_acondi_tiroideos_consolidated_final['FECHA LIBERACION V0_y'].combine_first(df_acondi_tiroideos_consolidated_final['FECHA LIBERACION V0'])
df_acondi_tiroideos_consolidated_final['FECHA REQ']           = pd.to_datetime(df_acondi_tiroideos_consolidated_final['FECHA REQ_y'], errors='coerce').combine_first( pd.to_datetime(df_acondi_tiroideos_consolidated_final['FECHA REQ'], errors='coerce'))
df_acondi_tiroideos_consolidated_final['FECHA OTIF']          = pd.to_datetime(df_acondi_tiroideos_consolidated_final['FECHA OTIF_y'], errors='coerce').combine_first( pd.to_datetime(df_acondi_tiroideos_consolidated_final['FECHA OTIF'], errors='coerce'))
df_acondi_tiroideos_consolidated_final['TYPE_BATCH']          = "E2E"
df_acondi_tiroideos_consolidated_final["PT_CANTIDAD C/YIELD"]= df_acondi_tiroideos_consolidated_final["PT_CANTIDAD"]

# Save the updated DataFrame to Excel
df_acondi_tiroideos_consolidated_final["LOTE PT"]=df_acondi_tiroideos_consolidated_final["LOTE PT"].apply(lambda x: x.strip())
df_acondi_tiroideos_consolidated_final["LOTE DE GRANEL"]=df_acondi_tiroideos_consolidated_final["LOTE DE GRANEL"].apply(lambda x: str(x).strip())
df_acondi_tiroideos_consolidated_final.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Acondi_Tiroideos_Consolidated.xlsx".format(base_address), index=False)

# Save DataFrame to Excel file with table formatting
# Save DataFrame to Excel file with table formatting
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Acondi_Tiroideos_Consolidated_1.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_acondi_tiroideos_consolidated_final.to_excel(writer, index=False, sheet_name='PL_Acondi_Tiroideos')
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['PL_Acondi_Tiroideos']
    # Create a table
    num_rows, num_cols = df_acondi_tiroideos_consolidated_final.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Acondi_Tiroides', 'columns': [{'header': col} for col in df_acondi_tiroideos_consolidated_final.columns]})
#cambio notable: reduccion a variable
# ### Solidos
columns_fabri_solidos_PLV=['Clave', 'Producto', 'Lote','Mezclado','ENTREGA MUESTRA',  'FECHA DE DICTAMEN']
columns_fabri_solidos_TAB12=['Clave', 'Producto', 'Lote','Recubrimiento','ENTREGA MUESTRA',  'LIBERACIÓN ANÁLISIS', 'UD', "CANTIDAD", "CANTIDAD C/YIELD", "Recurso", "Orden"]
columns_fabri_solidos_TAB13=['Clave', 'Producto', 'Lote','Recubrimiento','Compresión','ENTREGA MUESTRA',  'LIBERACIÓN ANÁLISIS', 'UD',  "CANTIDAD", "CANTIDAD C/YIELD", "Recurso", "Orden"]
columns_fabri_solidos_TAB19=['Clave', 'Producto', 'Lote','Recub','Compresión','ENTREGA MUESTRA',  'LIBERACIÓN ANÁLISIS' , 'UD', "CANTIDAD", "CANTIDAD C/YIELD", "Recurso", "Orden"]
columns_fabri_solidos_TAB24=['Clave', 'Producto', 'Lote','Compresión','ENTREGA MUESTRA',  'LIBERACIÓN ANÁLISIS', 'UD', "CANTIDAD", "CANTIDAD C/YIELD", "Recurso", "Orden"]
columns_fabri_solidos_ENV=['Clave', 'Producto', 'Lote', 'Lote Granel','Envasado','FECHA DE DICTAMEN', 'UD',  "CANTIDAD", "CANTIDAD C/YIELD", "Orden"]
columns_fabri_solidos_PLV=['Clave', 'Producto', 'Lote','Mezclado','ENTREGA MUESTRA','FECHA DE DICTAMEN', 'UD', "CANTIDAD", "Recurso", "Orden"]
columns_fabri_solidos_BT=['Clave', 'Producto', 'Lote','FIN','ENTREGA MUESTRA',  'LIBERACIÓN ANÁLISIS', "UD",  "CANTIDAD", "CANTIDAD C/YIELD","Recurso", "Orden"]

df_plan_solidos_fabri_TAB12 = clean_rows_based_on_prefix(plan_solidos_fabri_TAB12[columns_fabri_solidos_TAB12], 'Lote')
df_plan_solidos_fabri_TAB13 = clean_rows_based_on_prefix(plan_solidos_fabri_TAB13[columns_fabri_solidos_TAB13], 'Lote')
df_plan_solidos_fabri_TAB19 = clean_rows_based_on_prefix(plan_solidos_fabri_TAB19[columns_fabri_solidos_TAB19], 'Lote')
df_plan_solidos_fabri_TAB24 = clean_rows_based_on_prefix(plan_solidos_fabri_TAB24[columns_fabri_solidos_TAB24], 'Lote')
df_plan_solidos_fabri_ENV   = clean_rows_based_on_prefix(plan_solidos_fabri_ENV[columns_fabri_solidos_ENV], 'Lote')
df_plan_solidos_fabri_PLV   = clean_rows_based_on_prefix(plan_solidos_fabri_PLV[columns_fabri_solidos_PLV], 'Lote')

# For TAB13, add the FIN column comparing Recubrimiento and Compresion
df_plan_solidos_fabri_ENV["Recurso"] = "ENVASADO"

# Calculate the maximum and convert to datetime for TAB13
df_plan_solidos_fabri_TAB13= set_fin_column(df=df_plan_solidos_fabri_TAB13, column_name_1="Recubrimiento",column_name_2="Compresión")
df_plan_solidos_fabri_TAB19= set_fin_column(df=df_plan_solidos_fabri_TAB19, column_name_1="Recub",column_name_2="Compresión")

# Rename columns for TAB12 and TAB24
df_plan_solidos_fabri_TAB12.rename(columns={'Recubrimiento': 'FIN'}, inplace=True)
df_plan_solidos_fabri_TAB24.rename(columns={'Compresión': 'FIN'}, inplace=True)
df_plan_solidos_fabri_PLV.rename(columns={'Mezclado': 'FIN',
                                           'FECHA DE DICTAMEN': 'LIBERACIÓN ANÁLISIS'}, inplace=True)
df_plan_solidos_fabri_PLV["CANTIDAD C/YIELD"]=df_plan_solidos_fabri_PLV[["CANTIDAD"]]

# Stack the data frames
df_fabri_solidos_consolidated = pd.concat([df_plan_solidos_fabri_TAB12[columns_fabri_solidos_BT], 
                                           df_plan_solidos_fabri_TAB13[columns_fabri_solidos_BT], 
                                           df_plan_solidos_fabri_TAB19[columns_fabri_solidos_BT],
                                           df_plan_solidos_fabri_TAB24[columns_fabri_solidos_BT],
                                           df_plan_solidos_fabri_PLV[columns_fabri_solidos_BT]], 
                                           ignore_index=True)

# Create a mapping for renaming
rename_mapping = {
    'Clave': 'SKU',
    'Producto': 'DESCRIPCIÓN',
    'Lote': 'LOTE DE GRANEL',
    'FIN': 'FIN FABRI PLAN',
    'ENTREGA MUESTRA': 'PR_ENTREGA MUESTRA PLAN',
    'LIBERACIÓN ANÁLISIS': 'ENTREGA ÓRDEN ANALÍTICA PLAN',
    'CANTIDAD': 'GR_CANTIDAD',
    'CANTIDAD C/YIELD': 'GR_CANTIDAD C/YIELD',
    'Recurso': "RECURSO GR",
    'Orden':"ORDEN GR"}

# Rename the columns
df_fabri_solidos_consolidated.rename(columns=rename_mapping, inplace=True)
df_fabri_solidos_consolidated["PR_ENTREGA EXPEDIENTE GR PLAN"]= pd.to_datetime(df_fabri_solidos_consolidated["FIN FABRI PLAN"], errors="coerce")+ timedelta(days=7)
df_fabri_solidos_consolidated["LOTE DE GRANEL"]=df_fabri_solidos_consolidated["LOTE DE GRANEL"].apply(lambda x: x.strip())
df_fabri_solidos_consolidated.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Fabri_Solidos_Consolidated.xlsx".format(base_address), index=False)

with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Fabri_Solidos_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_fabri_solidos_consolidated.to_excel(writer, index=False, sheet_name='PL_Fabri_Solidos_Consolidated')
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['PL_Fabri_Solidos_Consolidated']
    # Create a table
    num_rows, num_cols = df_fabri_solidos_consolidated.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Fabri_Solidos_Consolidated', 'columns': [{'header': col} for col in df_fabri_solidos_consolidated.columns]})
#cambio notable: reduccion a variable
columns_solidos_acondi_L3=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_L4=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_L5=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_L6=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_L7=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_LC=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN',  "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
columns_solidos_acondi_LM=['CLAVE', 'DESCP', 'ORDEN', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN', "CANTIDAD", "CANTIDAD C/YIELD", "LINEA", "ORDEN"]
#cambio notable: reduccion a variable
columns_acondi_solidos_BT=      ['CLAVE', 'DESCP', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN', "CANTIDAD", "CANTIDAD C/YIELD", 'ORDEN', 'LINEA']
columns_acondi_solidos_BT_PLV=  ['CLAVE', 'DESCP', 'LOTE PT','LOTE GRANEL','COMENTARIOS','FIN', 'FECHA REQ CLIENTE','OTIF +14', 'FECHA DICTAMEN', "CANTIDAD", "CANTIDAD C/YIELD", 'ORDEN', 'ORDEN','LINEA']
columns_fabri_solidos_PLV=      ['Clave', 'Producto', 'Lote','Mezclado','ENTREGA MUESTRA','FECHA DE DICTAMEN']

#df_plan_solidos_fabri_PLV["LOTE PT"]           =df_plan_solidos_fabri_PLV[['LOTE PT']]
df_plan_solidos_fabri_PLV['FECHA REQ CLIENTE'] =df_plan_solidos_fabri_PLV[['LIBERACIÓN ANÁLISIS']]
df_plan_solidos_fabri_PLV['OTIF +14']          =df_plan_solidos_fabri_PLV[['LIBERACIÓN ANÁLISIS']]
df_plan_solidos_fabri_PLV['FECHA DICTAMEN']    =df_plan_solidos_fabri_PLV[['LIBERACIÓN ANÁLISIS']]
df_plan_solidos_fabri_PLV['COMENTARIOS']    = ""
df_plan_solidos_fabri_PLV.rename(columns={'Lote': 'LOTE GRANEL',
                                          'Clave': 'CLAVE', 
                                          'Producto': "DESCP",
                                           "Recurso": "LINEA",
                                            "Orden": "ORDEN" }, inplace=True)
# Create a mapping for renaming
rename_mapping = {
    'Clave': 'CLAVE',
    'Producto': 'DESCP',
    'Lote': 'LOTE PT',
    'FIN': 'FIN FABRI PLAN',
    'ENTREGA MUESTRA': 'PR_ENTREGA MUESTRA PLAN',
    'LIBERACIÓN ANÁLISIS': 'ENTREGA ÓRDEN ANALÍTICA PLAN'}

# Rename the columns
df_fabri_solidos_consolidated.rename(columns=rename_mapping, inplace=True)

df_plan_solidos_acondi_L3 = clean_rows_based_on_prefix(plan_solidos_acondi_L3[columns_solidos_acondi_L3], 'LOTE PT')
df_plan_solidos_acondi_L4 = clean_rows_based_on_prefix(plan_solidos_acondi_L4[columns_solidos_acondi_L4], 'LOTE PT')
df_plan_solidos_acondi_L5 = clean_rows_based_on_prefix(plan_solidos_acondi_L5[columns_solidos_acondi_L5], 'LOTE PT')
df_plan_solidos_acondi_L6 = clean_rows_based_on_prefix(plan_solidos_acondi_L6[columns_solidos_acondi_L6], 'LOTE PT')
df_plan_solidos_acondi_L7 = clean_rows_based_on_prefix(plan_solidos_acondi_L7[columns_solidos_acondi_L7], 'LOTE PT')
df_plan_solidos_acondi_LC = clean_rows_based_on_prefix(plan_solidos_acondi_LC[columns_solidos_acondi_LC], 'LOTE PT')
df_plan_solidos_acondi_LM = clean_rows_based_on_prefix(plan_solidos_acondi_LM[columns_solidos_acondi_LM], 'LOTE PT')


# Rename columns for TAB12 and TAB24, checar cambio de nombre para FIN just in case
df_plan_solidos_acondi_LM.rename(columns={'RETORNO': 'FIN', "OTIF PG +14": "OTIF +14"}, inplace=True)

# Stack the data frames
df_acondi_solidos_consolidated = pd.concat([df_plan_solidos_acondi_L3[columns_acondi_solidos_BT], 
                                           df_plan_solidos_acondi_L4[columns_acondi_solidos_BT], 
                                           df_plan_solidos_acondi_L5[columns_acondi_solidos_BT],
                                           df_plan_solidos_acondi_L6[columns_acondi_solidos_BT],
                                           df_plan_solidos_acondi_L7[columns_acondi_solidos_BT], 
                                           df_plan_solidos_acondi_LC[columns_acondi_solidos_BT]], ignore_index=True)
                                           #df_plan_solidos_fabri_PLV[columns_acondi_solidos_BT_PLV]
# Create a mapping for renaming
#cambio notable: diccionario
rename_mapping = {
    'CLAVE': 'SKU',
    'DESCP': 'DESCRIPCIÓN',
    'LOTE GRANEL': 'LOTE DE GRANEL',
    'LOTE PT': "LOTE PT",
    'COMENTARIOS': 'PL_STATUS',
    'FIN': 'ACO_FIN ACONDI PLAN',
    'FECHA DICTAMEN': 'FECHA LIBERACION V0',
    'FECHA REQ CLIENTE': 'FECHA REQ',
    'OTIF +14':'FECHA OTIF' ,
    'CANTIDAD': 'PT_CANTIDAD',
    'CANTIDAD C/YIELD': 'PT_CANTIDAD C/YIELD',
    "LINEA": "RECURSO PT",
    "ORDEN": "ORDEN PT"}

rename_mapping_maquila_sol = {
    'CLAVE': 'SKU',
    'DESCP': 'DESCRIPCIÓN',
    'LOTE GRANEL': 'LOTE DE GRANEL',
    'LOTE PT': "LOTE PT",
    'COMENTARIOS': 'PL_STATUS',
    'FIN': 'ACO_FIN ACONDI PLAN',
    'FECHA DICTAMEN': 'FECHA LIBERACION V0',
    'FECHA REQ CLIENTE': 'FECHA REQ',
    'OTIF +14':'FECHA OTIF' ,
    'CANTIDAD': 'PT_CANTIDAD',
    'CANTIDAD C/YIELD': 'PT_CANTIDAD C/YIELD',
    "LINEA": "RECURSO PT",
    "ORDEN": "ORDEN PT"}

# Rename the columns
df_acondi_solidos_consolidated.rename(columns=rename_mapping, inplace=True)
df_plan_solidos_acondi_LM.rename(columns=rename_mapping_maquila_sol, inplace=True)
df_acondi_solidos_consolidated["PT_ENTREGA EXPEDIENTE PLAN"]= pd.to_datetime(df_acondi_solidos_consolidated["ACO_FIN ACONDI PLAN"], errors="coerce")+ timedelta(days=4)
df_acondi_solidos_consolidated_final = df_acondi_solidos_consolidated.merge(
    df_plan_solidos_acondi_LM[['LOTE PT', 'ACO_FIN ACONDI PLAN', 'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF']],
    on='LOTE PT',
    how='left',
    suffixes=('', '_y')  # This will help avoid confusion with column names
)

# Update the values in the original DataFrame based on the merged DataFrame
df_acondi_solidos_consolidated_final['ACO_FIN ACONDI PLAN'] = pd.to_datetime(df_acondi_solidos_consolidated_final['ACO_FIN ACONDI PLAN_y'], errors='coerce').combine_first(pd.to_datetime(df_acondi_solidos_consolidated_final['ACO_FIN ACONDI PLAN'], errors='coerce'))
df_acondi_solidos_consolidated_final['FECHA LIBERACION V0'] = pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA LIBERACION V0_y'], errors='coerce').combine_first(pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA LIBERACION V0'], errors='coerce'))
df_acondi_solidos_consolidated_final['FECHA REQ']           = pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA REQ_y'], errors='coerce').combine_first( pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA REQ'], errors='coerce'))
df_acondi_solidos_consolidated_final['FECHA OTIF']          = pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA OTIF_y'], errors='coerce').combine_first( pd.to_datetime(df_acondi_solidos_consolidated_final['FECHA OTIF'], errors='coerce'))
df_acondi_solidos_consolidated_final['TYPE_BATCH']="E2E"
df_acondi_solidos_consolidated_final["LOTE PT"]=df_acondi_solidos_consolidated_final["LOTE PT"].apply(lambda x: x.strip())
df_acondi_solidos_consolidated_final["LOTE DE GRANEL"]=df_acondi_solidos_consolidated_final["LOTE DE GRANEL"].apply(lambda x: str(x).strip())
df_acondi_solidos_consolidated_final.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Acondi_Solidos_Consolidated.xlsx".format(base_address), index=False)
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Acondi_Solidos_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_acondi_solidos_consolidated_final.to_excel(writer, index=False, sheet_name='PL_Acondi_Solidos_Consolidated')    
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['PL_Acondi_Solidos_Consolidated']
    # Create a table
    num_rows, num_cols = df_acondi_solidos_consolidated_final.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Acondi_Solidos_Consolidated', 'columns': [{'header': col} for col in df_acondi_solidos_consolidated_final.columns]})

# ### Liquidos
columns_planning_BT=[ 'SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'FECHA REQ', 'FECHA OTIF','FIN FABRI PLAN', 
        'PR_ENTREGA MUESTRA PLAN',  'PR_ENTREGA EXPEDIENTE GR PLAN',
       'ENTREGA ÓRDEN ANALÍTICA PLAN','ACO_FIN ACONDI PLAN',
       'ENTREGA MUESTRA PT PLAN', 'PT_ENTREGA EXPEDIENTE PLAN',
       'PT_ENTREGA EXPEDIENTE REAL','FECHA LIBERACION V0',
       'FECHA LIBERACION ACTUAL', 'TW ID - ALL']
#cambio a implementar: reduccion a variable
columns_liquidos_fabri_NE=  ['CLAVE', 'PRODUCTO', 'LOTE', 'FIN', 'Entrega de muestra', 'Termino Análisis', 'COMENTARIOS',"CANTIDAD", "CANTIDAD C/YIELD", 'ORDEN']
columns_liquidos_fabri_AM=  ['CLAVE', 'PRODUCTO', 'LOTE','FIN','Entrega de muestra', 'Termino Análisis','COMENTARIOS',"CANTIDAD", "CANTIDAD C/YIELD", 'RECURSO', 'ORDEN']
columns_liquidos_fabri_DC=  ['CLAVE', 'PRODUCTO', 'LOTE',  'FIN', 'Entrega de muestra', 'Termino Análisis','COMENTARIOS', "CANTIDAD", "CANTIDAD C/YIELD", 'RECURSO', 'ORDEN']
columns_fabri_planning=     ['SKU', 'DESCRIPCIÓN', 'LOTE DE GRANEL','FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN',  'PR_ENTREGA EXPEDIENTE GR PLAN',
       'ENTREGA ÓRDEN ANALÍTICA PLAN', "CANTIDAD", "CANTIDAD C/YIELD", 'RECURSO', 'ORDEN']

df_liquidos_fabri_NE = clean_rows_based_on_prefix(plan_liquidos_fabri_NE[columns_liquidos_fabri_NE], 'LOTE')
df_liquidos_fabri_AM = clean_rows_based_on_prefix(plan_liquidos_fabri_AM[columns_liquidos_fabri_AM], 'LOTE')
df_liquidos_fabri_DC = clean_rows_based_on_prefix(plan_liquidos_fabri_DC[columns_liquidos_fabri_DC], 'LOTE')
df_liquidos_fabri_NE["RECURSO"]= "Liq Fab"

# Stack the data frames
df_fabri_liquidos_consolidated = pd.concat([df_liquidos_fabri_NE, df_liquidos_fabri_AM, df_liquidos_fabri_DC], ignore_index=True)

# Create a mapping for renaming
rename_mapping = {
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'LOTE': 'LOTE DE GRANEL',
    'FIN': 'FIN FABRI PLAN',
    'Entrega de muestra': 'PR_ENTREGA MUESTRA PLAN',
    'Termino Análisis': 'ENTREGA ÓRDEN ANALÍTICA PLAN',
    'COMENTARIOS': "PL_STATUS",
    'CANTIDAD': "GR_CANTIDAD",
    "CANTIDAD C/YIELD": "GR_CANTIDAD C/YIELD",
    "ORDEN":"ORDEN GR",
    "RECURSO": "RECURSO GR"}

# Rename the columns
df_fabri_liquidos_consolidated.rename(columns=rename_mapping, inplace=True)
df_fabri_liquidos_consolidated["PR_ENTREGA EXPEDIENTE GR PLAN"]= pd.to_datetime(df_fabri_liquidos_consolidated["FIN FABRI PLAN"], errors="coerce")+ timedelta(days=7)
df_fabri_liquidos_consolidated["LOTE DE GRANEL"]=df_fabri_liquidos_consolidated["LOTE DE GRANEL"].apply(lambda x: x.strip())
df_fabri_liquidos_consolidated.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Fabri_Liquidos_Consolidated.xlsx".format(base_address), index=False)

with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Fabri_Liquidos_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_fabri_liquidos_consolidated.to_excel(writer, index=False, sheet_name='PL_Fabri_Liquidos_Consolidated')    
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['PL_Fabri_Liquidos_Consolidated']
    # Create a table
    num_rows, num_cols = df_fabri_liquidos_consolidated.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Fabri_Liquidos_Consolidated', 'columns': [{'header': col} for col in df_fabri_liquidos_consolidated.columns]})

columns_liquidos_acondi_AM=[  'CLAVE', 'PRODUCTO', 'LOTE PT', 'LOTE GRANEL 1', 'LOTE GRANEL 2', 'Comentarios', 'FIN', 'FECHA DICTAMEN', 'Fecha de requerimiento','OTIF',"CANTIDAD", "CANTIDAD C/YIELD", "ORDEN"]
columns_liquidos_acondi_DC=[  'CLAVE', 'PRODUCTO', 'LOTE PT', 'LOTE GRANEL', 'Comentarios', 'FIN', 'FECHA DICTAMEN', 'Fecha de requerimiento','OTIF', "CANTIDAD", "CANTIDAD C/YIELD", "RECURSO", "ORDEN"]
columns_liquidos_acondi_NE=[  'CLAVE', 'PRODUCTO', 'LOTE PT', 'LOTE GRANEL', 'Comentarios', 'FIN', 'FECHA DICTAMEN', 'Fecha de requerimiento','OTIF', "CANTIDAD", "CANTIDAD C/YIELD", "ORDEN"]
columns_acondi_planning= ['SKU', 'DESCRIPCIÓN','LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 
                           "PL_STATUS", 'ACO_FIN ACONDI PLAN','FECHA LIBERACION V0','FECHA REQ',
                             'FECHA OTIF', "CANTIDAD", "CANTIDAD C/YIELD", "RECURSO", "ORDEN"]
df_liquidos_acondi_NE = clean_rows_based_on_prefix(plan_liquidos_acondi_NE[columns_liquidos_acondi_NE], 'LOTE PT')
df_liquidos_acondi_AM = clean_rows_based_on_prefix(plan_liquidos_acondi_AM[columns_liquidos_acondi_AM], 'LOTE PT')
df_liquidos_acondi_DC = clean_rows_based_on_prefix(plan_liquidos_acondi_DC[columns_liquidos_acondi_DC], 'LOTE PT')
df_liquidos_acondi_AM["RECURSO"]="L1"
df_liquidos_acondi_NE["RECURSO"]="TREN 1"

# Rename "LOTE GRANEL 1" to "LOTE GRANEL" and create "LOTE GRANEL 2" for AM and DC
df_liquidos_acondi_AM.rename(columns={'LOTE GRANEL 1': 'LOTE GRANEL'}, inplace=True)
df_liquidos_acondi_DC['LOTE GRANEL 2'] = pd.NA  # Create empty column
df_liquidos_acondi_NE['LOTE GRANEL 2'] = pd.NA  # Create empty column

# Create a mapping for renaming
rename_mapping = {
    'CLAVE': 'SKU',
    'PRODUCTO': 'DESCRIPCIÓN',
    'LOTE GRANEL': 'LOTE DE GRANEL',
    'LOTE GRANEL 2': 'LOTE DE GRANEL 2',
    'Comentarios': 'PL_STATUS',
    'FIN':  'ACO_FIN ACONDI PLAN',
    'FECHA DICTAMEN': 'FECHA LIBERACION V0',
    'Fecha de requerimiento': 'FECHA REQ',
    'OTIF':'FECHA OTIF',
    'CANTIDAD': "PT_CANTIDAD",
    "CANTIDAD C/YIELD": "PT_CANTIDAD C/YIELD",
    "RECURSO": "RECURSO PT",
    "ORDEN": "ORDEN PT"}

# Rename the columns
df_acondi_liquidos_consolidated = pd.concat([df_liquidos_acondi_NE, df_liquidos_acondi_AM, df_liquidos_acondi_DC], ignore_index=True)
df_acondi_liquidos_consolidated.rename(columns=rename_mapping, inplace=True)
df_acondi_liquidos_consolidated["PT_ENTREGA EXPEDIENTE PLAN"]= pd.to_datetime(df_acondi_liquidos_consolidated["ACO_FIN ACONDI PLAN"], errors="coerce")+ timedelta(days=4)
df_acondi_liquidos_consolidated["LOTE DE GRANEL"]            = df_acondi_liquidos_consolidated["LOTE DE GRANEL"].apply(lambda x: str(x).strip())
df_acondi_liquidos_consolidated["LOTE DE GRANEL 2"]          = df_acondi_liquidos_consolidated["LOTE DE GRANEL 2"].apply(lambda x: str(x).strip())
df_acondi_liquidos_consolidated["LOTE PT"]                   = df_acondi_liquidos_consolidated["LOTE PT"].apply(lambda x: x.strip())
df_acondi_liquidos_consolidated.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\PL_Acondi_Liquidos_Consolidated.xlsx".format(base_address), index=False)

with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\PL_Acondi_Liquidos_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    df_acondi_liquidos_consolidated.to_excel(writer, index=False, sheet_name='PL_Acondi_Liquidos_Consolidated')    
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['PL_Acondi_Liquidos_Consolidated']
    # Create a table
    num_rows, num_cols = df_acondi_liquidos_consolidated.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'Acondi_Liquidos_Consolidated', 'columns': [{'header': col} for col in df_acondi_liquidos_consolidated.columns]})

# ### BatchTracker Solids
df_acondi =df_acondi_solidos_consolidated_final.copy()
df_fabri  =df_fabri_solidos_consolidated.copy()
BT_solidos=merge_fabri_to_acondi(df_acondi=df_acondi,
                                 df_fabri=df_fabri,
                                 family="solids",
                                 liberacion_granel="UD")
BT_solidos["PLAN"]="Solids"
BT_solidos=update_lote_pt(BT_solidos, plan_solidos_fabri_ENV)
BT_solidos.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\BT_Solids.xlsx".format(base_address), index=False)
BT_solidos=BT_solidos[['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'PL_STATUS',
        'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF',
        'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 'PR_ENTREGA EXPEDIENTE GR PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN',
        'ACO_FIN ACONDI PLAN','PT_ENTREGA EXPEDIENTE PLAN',
        'TYPE_BATCH', 'BT_analysis', "PLAN", "GR_CANTIDAD C/YIELD", "GR_CANTIDAD", "PT_CANTIDAD C/YIELD", "PT_CANTIDAD",
           "ORDEN GR",  "ORDEN PT", "RECURSO PT", "RECURSO GR"]]

# ### BatchTracker Liquids
df_acondi =df_acondi_liquidos_consolidated.copy()
df_fabri  =df_fabri_liquidos_consolidated.copy()
BT_liquidos,_=merge_and_process_batches(df_acondi=df_acondi,
                                 df_fabri=df_fabri)
BT_liquidos["PLAN"]="Liquids"
BT_liquidos.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\BT_Liquidos.xlsx".format(base_address), index=False)    

# ### BatchTracker Tiroides
df_acondi =df_acondi_tiroideos_consolidated_final.copy()
df_fabri  =df_fabri_tiroideos_consolidated.copy()
BT_tiroideos=merge_fabri_to_acondi(df_acondi=df_acondi,
                                 df_fabri=df_fabri,
                                 family="tyroids",
                                 liberacion_granel="Dictámen")
BT_tiroideos["PLAN"]="Tyroids"
BT_tiroideos['FECHA LIBERACION V0'] = BT_tiroideos['FECHA LIBERACION V0'].fillna(BT_tiroideos['Dictámen'])
BT_tiroideos.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\BT_Tiroideos.xlsx".format(base_address), index=False)

# ### BatchTracker Consolidation
BT_liquidos.rename(columns={"PL_STATUS_x": "PL_STATUS"}, inplace=True)
BT_solidos.rename(columns={"PL_STATUS_x": "PL_STATUS"}, inplace=True)
final_columns_BT =['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'PL_STATUS',
        'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF',
        'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 'PR_ENTREGA EXPEDIENTE GR PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN',
        'ACO_FIN ACONDI PLAN','PT_ENTREGA EXPEDIENTE PLAN',
        'TYPE_BATCH', 'BT_analysis', "PLAN", "GR_CANTIDAD C/YIELD", "GR_CANTIDAD", "PT_CANTIDAD C/YIELD", "PT_CANTIDAD",
          "ORDEN GR", "ORDEN PT", "RECURSO PT", "RECURSO GR"]
final_columns_BT_duple =['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'PL_STATUS',
        'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF',
        'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 'PR_ENTREGA EXPEDIENTE GR PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN',
        'ACO_FIN ACONDI PLAN','PT_ENTREGA EXPEDIENTE PLAN',
        'TYPE_BATCH', 'BT_analysis', "PLAN", "GR_CANTIDAD C/YIELD", "GR_CANTIDAD", "PT_CANTIDAD C/YIELD", "PT_CANTIDAD",
          "ORDEN GR", "ORDEN PT","ORDEN PT", "RECURSO PT", "RECURSO GR"]
BT_tiroideos_month = filter_by_date(BT_tiroideos[final_columns_BT_duple], year=[2025,2026],months=[1,2,3,4,5,6,7,8,9,10,11,12])
BT_liquidos_month = filter_by_date(BT_liquidos[final_columns_BT_duple], year=[2025,2026],months=[1,2,3,4,5,6,7,8,9,10,11,12])
BT_solidos_month = filter_by_date(BT_solidos[final_columns_BT], year=[2025,2026],months=[1,2,3,4,5,6,7,8,9,10,11,12])
BatchTracker_consolidated_plan = pd.concat([BT_tiroideos_month, BT_liquidos_month, BT_solidos_month], ignore_index=True)

# Load your DataFrame (assuming it's already defined as BatchTracker_consolidated_plan)
BatchTracker_consolidated_plan = BatchTracker_consolidated_plan[['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2', 'PL_STATUS',
        'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF',
        'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN', 'PR_ENTREGA EXPEDIENTE GR PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN',
        'ACO_FIN ACONDI PLAN','PT_ENTREGA EXPEDIENTE PLAN',
        'TYPE_BATCH', 'BT_analysis', "PLAN", "GR_CANTIDAD C/YIELD", "GR_CANTIDAD", "PT_CANTIDAD C/YIELD", "PT_CANTIDAD",
        "ORDEN GR", "ORDEN PT", "RECURSO GR", "RECURSO PT"]]
BatchTracker_consolidated_plan['SKU'] = BatchTracker_consolidated_plan['SKU'].apply(lambda x: str(x).replace(".",""))

#BatchTracker_consolidated_plan["Planning_Consistency"] = np.where(
#    BatchTracker_consolidated_plan['ENTREGA ÓRDEN ANALÍTICA PLAN'] >= BatchTracker_consolidated_plan['FECHA LIBERACION V0'],
#    'Inconsistente',
#    'Consistente')
# List of date columns to format
date_columns = ['FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF', 'FIN FABRI PLAN', 'PR_ENTREGA MUESTRA PLAN',
                'PR_ENTREGA EXPEDIENTE GR PLAN', 'ENTREGA ÓRDEN ANALÍTICA PLAN', 'ACO_FIN ACONDI PLAN', 'PT_ENTREGA EXPEDIENTE PLAN']

# Formatting the date columns to 'YYYY/MM/DD'
for col in date_columns:
    BatchTracker_consolidated_plan[col] = pd.to_datetime(BatchTracker_consolidated_plan[col], errors='coerce').dt.normalize()

# Save the updated DataFrame to Excel
BatchTracker_consolidated_plan.to_excel(r"{0}\Digitalización - Documents\DigitalProjectsLibrary\Calibration\Tendencias\OTIF\ConsolidatedDB\BatchTracker_allV0_today.xlsx".format(base_address), index=False)

# Save DataFrame to Excel file with table formatting
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\BT_PLAN_Consolidated_allV0.xlsx".format(base_address), engine='xlsxwriter') as writer:
    BatchTracker_consolidated_plan.to_excel(writer, index=False, sheet_name='BT_consolidates')
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['BT_consolidates']    
    # Create a table
    num_rows, num_cols = BatchTracker_consolidated_plan.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'DataTable', 'columns': [{'header': col} for col in BatchTracker_consolidated_plan.columns]})
# ## Concatenación QA
# # Building BatchTracker
BatchTracker_consolidated_plan["PR_Estatus"]="1"
BatchTracker_consolidated_plan["QC_Estatus"]="1"
BatchTracker_df["PR_Estatus"]="1"
BatchTracker_df["QC_Estatus"]="1"
combined_Fabri_df.to_csv("combined_Fabri_df.csv", index=False)
combined_qc_df.to_csv("combined_qc_df.csv", index=False)
combined_acondi_df.to_csv("combined_acondi_df.csv", index=False)
for target_df in [BatchTracker_consolidated_plan, BatchTracker_df]:
    for index, row in combined_Fabri_df.iterrows():
        row = row.replace(' ', pd.NaT)
        lote = row['LOTE DE GRANEL']
        if (lote in target_df['LOTE PT'].values)or \
           (lote in target_df['LOTE DE GRANEL'].values) or \
           (lote in target_df['LOTE DE GRANEL 2'].values):
                # Update FIN FABRI REAL
                target_df.loc[(target_df['LOTE PT']          == lote), 'FIN FABRI REAL'] = row['FIN FABRI REAL']
                target_df.loc[(target_df['LOTE DE GRANEL 2'] == lote), 'FIN FABRI REAL'] = row['FIN FABRI REAL']
                target_df.loc[(target_df['LOTE DE GRANEL']   == lote), 'FIN FABRI REAL'] = row['FIN FABRI REAL']
                # Update PR_ESTATUS
                target_df.loc[(target_df['LOTE PT']          == lote), "PR_Estatus"] = row["PR_Estatus"]
                target_df.loc[(target_df['LOTE DE GRANEL 2'] == lote), "PR_Estatus"] = row["PR_Estatus"]
                target_df.loc[(target_df['LOTE DE GRANEL']   == lote), "PR_Estatus"] = row["PR_Estatus"]
                # Update PR_entrega expediente de GR real
                target_df.loc[(target_df['LOTE PT']          == lote), 'PR_ENTREGA EXPEDIENTE GR REAL'] = row['PR_ENTREGA EXPEDIENTE GR REAL']
                target_df.loc[(target_df['LOTE DE GRANEL 2'] == lote), 'PR_ENTREGA EXPEDIENTE GR REAL'] = row['PR_ENTREGA EXPEDIENTE GR REAL']
                target_df.loc[(target_df['LOTE DE GRANEL']   == lote), 'PR_ENTREGA EXPEDIENTE GR REAL'] = row['PR_ENTREGA EXPEDIENTE GR REAL']
    for index, row in combined_acondi_df.iterrows():
        row = row.replace(' ', pd.NaT)
        lote =row['LOTE PT']
        sku = row['SKU']
        if (lote in target_df['LOTE PT'].values)&(sku in target_df['SKU'].values) or \
           (lote in target_df['LOTE DE GRANEL'].values)&(sku in target_df['SKU'].values) or \
           (lote in target_df['LOTE DE GRANEL 2'].values)&(sku in target_df['SKU'].values):
               # Update aco_fin acondi real
               target_df.loc[(target_df['LOTE PT']           == lote)&(target_df['SKU'] == sku), 'ACO_FIN ACONDI REAL'] = row['ACO_FIN ACONDI REAL']
               target_df.loc[(target_df['LOTE DE GRANEL 2']  == lote)&(target_df['SKU'] == sku), 'ACO_FIN ACONDI REAL'] = row['ACO_FIN ACONDI REAL']
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote)&(target_df['SKU'] == sku), 'ACO_FIN ACONDI REAL'] = row['ACO_FIN ACONDI REAL']
               # Update pt_entrega expediente real
               target_df.loc[(target_df['LOTE PT']           == lote)&(target_df['SKU'] == sku), 'PT_ENTREGA EXPEDIENTE REAL'] =  pd.to_datetime(row['PT_ENTREGA EXPEDIENTE REAL']).date()
    for index, row in combined_qc_df.iterrows():
        row = row.replace(' ', pd.NaT)
        lote = row['LOTE']
        #sku = row['SKU']
        if (lote in target_df['LOTE PT'].values) or \
           (lote in target_df['LOTE DE GRANEL'].values) or \
           (lote in target_df['LOTE DE GRANEL 2'].values):
            #seccion de Batchtracker normal 
           if target_df is BatchTracker_df:
               # Update BatchTracker_df with values from combined_Fabri_df
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), 'PR_ENTREGA MUESTRA REAL'] = row['PR_ENTREGA MUESTRA REAL']
               # Update BatchTracker_df with values from combined_Fabri_df
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), "QC_Estatus"] = row["QC_Estatus"]
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), 'ENTREGA ÓRDEN ANALÍTICA REAL'] = row['ENTREGA ÓRDEN ANALÍTICA REAL']    
           else:
               #seccion de Batchtracker consolidated
               # Update PR_ENTREGA MUESTRA REAL
               target_df.loc[(target_df['LOTE PT']           == lote), 'PR_ENTREGA MUESTRA REAL'] = row['PR_ENTREGA MUESTRA REAL']
               target_df.loc[(target_df['LOTE DE GRANEL 2']  == lote), 'PR_ENTREGA MUESTRA REAL'] = row['PR_ENTREGA MUESTRA REAL']
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), 'PR_ENTREGA MUESTRA REAL'] = row['PR_ENTREGA MUESTRA REAL']
               # Update QC_Estatus
               target_df.loc[(target_df['LOTE PT']           == lote), "QC_Estatus"] = row["QC_Estatus"]
               target_df.loc[(target_df['LOTE DE GRANEL 2']  == lote), "QC_Estatus"] = row["QC_Estatus"]
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), "QC_Estatus"] = row["QC_Estatus"]
                   # Update Entrega orden analitica real
               target_df.loc[(target_df['LOTE PT']           == lote), 'ENTREGA ÓRDEN ANALÍTICA REAL'] = row['ENTREGA ÓRDEN ANALÍTICA REAL']
               target_df.loc[(target_df['LOTE DE GRANEL 2']  == lote), 'ENTREGA ÓRDEN ANALÍTICA REAL'] = row['ENTREGA ÓRDEN ANALÍTICA REAL']
               target_df.loc[(target_df['LOTE DE GRANEL']    == lote), 'ENTREGA ÓRDEN ANALÍTICA REAL'] = row['ENTREGA ÓRDEN ANALÍTICA REAL']

"""
Tenemos el problema que aqui la construccion de BatchTracker_df usa menos indicaciones que el de consolidated_plan
la idea va a ser integrar un if para ver si de esa manera el loop identifica cual version usar. 
Si esto es exitoso se podria integrar el flujo de las 3 bases de datos a un solo flujo o funcion en 
vez de tener 3 versiones diferentes para los tres documentos ya que todas tienen 
basicamente el mismo if para todas las secciones. 
"""
# Apply the function to each row of BatchTracker_df and create the new column
BatchTracker_consolidated_plan['Deviation_Info'] = BatchTracker_consolidated_plan.apply(create_deviation_info, axis=1)
# Apply the function to each row of BatchTracker_df and create the new column 'Deviation Due Date'
BatchTracker_consolidated_plan['Deviation Due Date'] = BatchTracker_consolidated_plan.apply(create_deviation_due_date, axis=1)
# Apply the function to each row of BatchTracker_df and create the new column 'Deviation Due Date'
BatchTracker_consolidated_plan['Deviation Close Date'] = BatchTracker_consolidated_plan.apply(create_deviation_closure_date, axis=1)
# Convert the new columns to datetime
BatchTracker_consolidated_plan['Deviation Due Date'] = pd.to_datetime(BatchTracker_consolidated_plan['Deviation Due Date'], errors='coerce',dayfirst=True)
BatchTracker_consolidated_plan['Deviation Close Date'] = pd.to_datetime(BatchTracker_consolidated_plan['Deviation Close Date'], errors='coerce',dayfirst=True)
BatchTracker_consolidated_plan = BatchTracker_consolidated_plan[['SKU', 'DESCRIPCIÓN', 'LOTE PT', 'LOTE DE GRANEL', 'LOTE DE GRANEL 2',
       'PL_STATUS', 'FECHA LIBERACION V0', 'FECHA REQ', 'FECHA OTIF',
       'FIN FABRI PLAN', 'FIN FABRI REAL', 
       'PR_ENTREGA MUESTRA PLAN',  'PR_ENTREGA MUESTRA REAL',
       'PR_ENTREGA EXPEDIENTE GR PLAN', 'PR_ENTREGA EXPEDIENTE GR REAL',
       'ENTREGA ÓRDEN ANALÍTICA PLAN', 'ENTREGA ÓRDEN ANALÍTICA REAL',
       'ACO_FIN ACONDI PLAN', 'ACO_FIN ACONDI REAL',
       'PT_ENTREGA EXPEDIENTE PLAN', 'PT_ENTREGA EXPEDIENTE REAL',
        'TYPE_BATCH',
       'BT_analysis', 'PLAN', 'GR_CANTIDAD C/YIELD', 'GR_CANTIDAD',
       'PT_CANTIDAD C/YIELD', 'PT_CANTIDAD', 'PR_Estatus', 'QC_Estatus',
       'Deviation_Info', 'Deviation Due Date','Deviation Close Date']]
# Formatting the date columns to 'YYYY/MM/DD'
for col in date_columns:
    BatchTracker_consolidated_plan[col] = pd.to_datetime(BatchTracker_consolidated_plan[col], errors='coerce').dt.normalize()
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\MasterBT_Consolidated.xlsx".format(base_address), engine='xlsxwriter') as writer:
    BatchTracker_consolidated_plan.to_excel(writer, index=False, sheet_name='BT_consolidates')   
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['BT_consolidates']
    # Create a table
    num_rows, num_cols = BatchTracker_consolidated_plan.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'DataTable', 'columns': [{'header': col} for col in BatchTracker_consolidated_plan.columns]})
BatchTracker_consolidated_plan.to_excel("MasterBatchTracker.xlsx")
BatchTracker_df.to_excel("Dummy_batch_tracker.xlsx")
# Save DataFrame to Excel file with table formatting
with pd.ExcelWriter(r"{0}\Seguimiento Servicio GMS P&G-BP - TrackWise_Deviations\Consolidated_BT_Deviations.xlsx".format(base_address), engine='xlsxwriter') as writer:
    BatchTracker_df.to_excel(writer, index=False, sheet_name='TW')
    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['TW']
    # Create a table
    num_rows, num_cols = BatchTracker_df.shape
    worksheet.add_table(0, 0, num_rows, num_cols - 1, {'name': 'DataTable', 'columns': [{'header': col} for col in BatchTracker_df.columns]})
    fin = perf_counter()
tiempo_total = fin - inicio
minutos, segundos = divmod(tiempo_total, 60)
print(
    f"Tiempo total de ejecución: "
    f"{int(minutos)} minutos y {segundos:.2f} segundos"
    f"Batchtracker is cooked")