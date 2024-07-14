# region: Initialization
import os
import json
from tavily import TavilyClient
import base64
from PIL import Image
import io
import re
from anthropic import Anthropic, APIStatusError, APIError
import difflib
import time
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from dataclasses import dataclass

console = Console()

from dotenv import load_dotenv
import chardet

# try to load the .env file. If it doesn't exist, the code will continue without it
load_dotenv()

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Models to use
MAINMODEL = "claude-3-5-sonnet-20240620"
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"

# Initialize the Anthropic client
if "ANTHROPIC_API_KEY" in os.environ:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)
else:
    client = Anthropic(api_key="YOUR KEY")

# Initialize the Tavily client
if "TAVILY_API_KEY" in os.environ:
    api_key = os.environ["TAVILY_API_KEY"]
    tavily = TavilyClient(api_key=api_key)
else:
    tavily = TavilyClient(api_key="YOUR KEY")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False
# endregion: Initialization

# region: Native prompts
# Base system prompt
base_system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

1. Creating project structures, including folders and files
2. Writing clean, efficient, and well-documented code
3. Debugging complex issues and providing detailed explanations
4. Offering architectural insights and design patterns
5. Staying up-to-date with the latest technologies and industry trends
6. Reading and analyzing existing files in the project directory
7. Listing files in the root directory of the project
8. Performing web searches to get up-to-date information or additional context
9. When you use search, make sure you use the best query to get the most accurate and up-to-date information
10. Analyzing images provided by the user

Available tools and when to use them:

1. create_folder: Use this tool to create a new folder at a specified path.
   Example: When setting up a new project structure.

2. create_file: Use this tool to create a new file at a specified path with content.
   Example: When creating new source code files or configuration files.

3. search_file: Use this tool to search for specific patterns in a file and get the line numbers where the pattern is found. This is especially useful for large files.
   Example: When you need to locate specific functions or variables in a large codebase.

4. edit_file: Use this tool to edit a specific range of lines in a file. You should use this after using search_file to identify the lines you want to edit.
   Example: When you need to modify a specific function or block of code.

5. read_file: Use this tool to read the contents of a file at a specified path.
   Example: When you need to examine the current content of a file before making changes.

6. list_files: Use this tool to list all files and directories in a specified folder (default is the current directory).
   Example: When you need to understand the current project structure or find specific files.

7. tavily_search: Use this tool to perform a web search and get up-to-date information or additional context.
   Example: When you need current information about a technology, library, or best practice.

8. list_files_recursively: Use this tool to list all files and directories in a specified folder and its subdirectories.

IMPORTANT: For file modifications, always use the search_file tool first to identify the lines you want to edit, then use the edit_file tool to make the changes. This two-step process ensures more accurate and targeted edits.

Follow these steps when editing files:
1. Use the read_file tool to examine the current contents of the file you want to edit.
2. For longer files, use the search_file tool to find the specific lines you want to edit.
3. Use the edit_file tool with the line numbers returned by search_file to make the changes.

This approach will help you make precise edits to files of any size or complexity.

When asked to create a project:
- Always start by creating a root folder for the project using the create_folder tool.
- Then, create the necessary subdirectories and files within that root folder using the create_folder and create_file tools.
- Organize the project structure logically and follow best practices for the specific type of project being created.

When asked to make edits or improvements:
- ALWAYS START by using the read_file tool to examine the contents of existing files.
- Use the search_file tool to locate the specific lines you want to edit.
- Use the edit_file tool to make the necessary changes.
- Analyze the code and suggest improvements or make necessary edits.
- Pay close attention to the existing code structure.
- Ensure that you're replacing old code with new code, not just adding new code alongside the old.
- After making changes, always re-read the entire file to check for any unintended duplications.
- If you notice any duplicated code after your edits, immediately remove the duplication and explain the correction.

Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

Always strive to provide the most accurate, helpful, and detailed responses possible. If you're unsure about something, admit it and consider using the tavily_search tool to find the most current information.
"""

# Auto mode-specific system prompt
automode_system_prompt = """
You are currently in automode!!!

When in automode:
1. Set clear, achievable goals for yourself based on the user's request
2. Work through these goals one by one, using the available tools as needed
3. REMEMBER!! You can read files, write code, search for specific lines of code to make edits and list the files, search the web. Use these tools as necessary to accomplish each goal
4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
5. ALWAYS READ A FILE AFTER EDITING IT. So you can see if you made any unintended changes or duplications.
5. IMPORTANT RULE!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself. If you think you've achieved the results established in the original request, say "AUTOMODE_COMPLETE" in your response to exit the loop!
6. You have access to this {iteration_info} amount of iterations you have left to complete the request. Use this information to make decisions and to provide updates on your progress, knowing the number of responses you have left to complete the request.

YOU NEVER ASK "Is there anything else you'd like to add or modify in the project or code?" or "Is there anything else you'd like to add or modify in the project?" or anything like that once you feel the request is complete. just say "AUTOMODE_COMPLETE" in your response to exit the loop!
"""
# endregion: Native prompts

# region: Sonar prompts

@dataclass
class SonarPrompts:
    what_is_sonar: str
    sonar_folder_structure: str

def get_sonar_prompts() -> SonarPrompts:
    what_is_sonar = """
      Sonar is a multi-tenant, multi-app platform that allows you to build and deploy your own frontend web apps. It provides an automated API that manages communication between the frontend and backend systems. The backend is a relational database off which the automated API is built.

      Here are the key concepts you need to know about Sonar:
      - Apps: An App is a frontend system definition. An App is mostly or completely defined in a folder of shape `src/apps/<app_name>`.
      - LocalEntity: A LocalEntity is a TypeScript object that represents a table in the database. It is used to define the structure of the table and the data that is displayed in the app.
      - RemoteEntity: A RemoteEntity is a SQL query that represents a table in the database. It is used to define the structure of the table and the data that is displayed in the app.

      Your help may be requested for the following tasks:
      1. Creating new Apps
      2. Developing LocalEntity and RemoteEntity definitions
      3. Defining the menu structure for an App
      4. Connecting an App to the Sonar platform
    """
    
    how_to_create_app = """

    """

    sonar_prompt = """
        Currently, you are working with Sonar. Sonar is multi-tenant multi-app platform. It has nothing to do with epynomous code quality tool.
        It is a platform that allows you to build and deploy your own frontent web apps (Apps), using automated API that manages communication between the frontend and backend systems.
        Backend is relational database off which the automated API is built.

        Here are the concepts you need to know:
        **Apps**: An App is a frontend system definition. An App mostly or completely defined in a folder of shape src/apps/<app_name>.
        **LocalEntity**: LocalEntity is a TypeScript object that represents a table in the database. It is used to define the structure of the table and the data that is displayed in the app.
        **RemoteEntity**: RemoteEntity is a SQL query that represents a table in the database. It is used to define the structure of the table and the data that is displayed in the app.

        Your help may be asked for the following tasks:
        ** Creating new Apps **
        1. ask user for the name of the App folder to create, then use tool copy_folder_with_content to copy src/apps/_template to src/apps/<app_name>
        2. ask user for display name of the App, then use tool replace_string_in_file to replace 'Example title' with the display name in src/apps/<app_name>/index.ts
        3. ask user whether she has a text file with a description of what the App should do.
            3a. If yes, ask them to place the file in the folder /specs.
            3b. If no, engage them in the chat to get a sense of what the App should do. Then, create a file in /specs with the description; name it generated_from_chat_[YYYYMMDD_HHMM].txt
        4. Read the file in /specs and develop it further:
            4a. Construct entity relationship diagram (ERD) for the App. Save its mermaidjs representation in /specs/erd.md
            Example:
            ~~~mermaid
                %%{init: {'theme':'neutral'}}%%
                erDiagram
                    EVENT ||--o{ SIGNAL : has
                    EVENT {
                    int ID
                    timestamp CreatedAt
                    int CreatedBy
                    int EventStatus
                    int Building
                    int Area
                    int IOPSStage
                    int ProcessStep
                    int Product
                    string DetectedAt
                    string OccurredAt
                    int DetectedBy
                    string QCTestingRequiredFlag
                    int SampleSubmittedToQCLabBy
                    int QCTestingSubmittedBy
                    int TriageLead
                    }
                    EVENT ||--o{ TRIAGE_PARTICIPANT : has
                    SIGNAL ||--|{ SIGNAL_TYPE : has
                    SIGNAL {
                    int ID
                    timestamp CreatedAt
                    int CreatedBy
                    int EventID
                    int SignalTypeID
                    }
                    TRIAGE_PARTICIPANT ||--|{ USER : has
                    TRIAGE_PARTICIPANT {
                    int ID
                    timestamp CreatedAt
                    int CreatedBy
                    int EventID
                    int UserID
                    int OrgFunction
                    }
                    TRIAGE_PARTICIPANT ||--|{ ORG_FUNCTION : has
                    EVENT ||--|{ BUILDING : has
                    EVENT ||--|{ AREA : has
                    EVENT ||--|{ IOPS_STAGE : has
                    EVENT ||--|{ PROCESS_STEP : has
                    EVENT ||--|{ PRODUCT : has
                    EVENT ||--|{ EVENT_STATUS : has
                    EVENT ||--|{ USER : has
                    SIGNAL_TYPE ||--|{ SIGNAL_CATEGORY_LEVEL_1 : has
                    SIGNAL_TYPE {
                    int ID
                    int ProductID
                    int ProcessStepID
                    int IOPStageID
                    int AreaID
                    int OrgID
                    int PostSignalCaptureActionID
                    int RiskLevelID
                    int SignalCategoryLevel1ID
                    int SignalCategoryLevel2ID
                    int SignalCategoryLevel3ID
                    int SignalCategoryLevel4ID
                    int SignalCategoryLevel5ID
                    string SignalTypeName
                    string SignalTypeDescription
                    }
                    SIGNAL_TYPE ||--|{ SIGNAL_CATEGORY_LEVEL_2 : has
                    SIGNAL_TYPE ||--|{ SIGNAL_CATEGORY_LEVEL_3 : has
                    SIGNAL_TYPE ||--|{ SIGNAL_CATEGORY_LEVEL_4 : has
                    SIGNAL_TYPE ||--|{ SIGNAL_CATEGORY_LEVEL_5 : has
                    SIGNAL_TYPE ||--|{ RISK_LEVEL : has
                    SIGNAL_TYPE ||--|{ POST_SIGNAL_CAPTURE_ACTION : has
                    SIGNAL_TYPE ||--|{ ORG : has
                    SIGNAL_TYPE ||--|{ AREA : has
                    SIGNAL_TYPE ||--|{ PROCESS_STEP : has
                    SIGNAL_TYPE ||--|{ IOPS_STAGE : has
                    SIGNAL_TYPE ||--|{ PRODUCT : has
                ~~~
            4b. Construct a list of entities and their relationships. Save it in /specs/entities.md
            4c. Construct our best shot view of the App's menu. Save it in /specs/menu.md
                Example:
                    # Application Menu Structure

                    ## Submit Event
                    - Create new Event
                    - Drafts

                    ## Events by Status
                    - Awaiting sample submission
                    - Awaiting test results
                    - Processing stage
                    - Resulted in Minor Deviation
                    - Resulted in Deviation with additional investigation
                    - Track & Trend
                    - Deleted

                    ## Events' Signals
                    - Signals

                    ## Master data
                    - Event statuses
                    - Event localization dimensions
                    - Products
                    - DMS Stages
                    - Areas
                    - Process Steps
                    - Buildings
                    - Org Functions

                    ## Signal types
                    - Signal categories
                    - Signal categories, level 1
                    - Signal categories, level 2
                    - Signal categories, level 3
                    - Signal categories, level 4
                    - Signal categories, level 5
                    - Signal attributes
                    - Risk levels
                    - Post signal capture actions
                    - Deviation categories
                    - Post deviation determination actions

                    ## Documentation
                    - Event state transition diagram
                    - FRD

                    ## User management
                    - Create user
                    - User list
                    - Login attempts
                    - Roles
                    - Impersonate user
        5. Add new LocalEntityNames (from 4b) to src/types/localEntityNames.ts by using replace_string_in_file tool.
            Example:
                to-be-replaced string:
                `export type LocalEntityName =`
                new string:
                `export type LocalEntityName =
                'app31.statuses' |
                'app31.risks' |`
        6. Add new RemoteEntityNames (from 4b) to src/types/remoteEntityNames.ts by using replace_string_in_file tool.
            For now assume that RemoteEntityNames are 1-to-1 with LocalEntityNames.
            Example:
                to-be-replaced string:
                `export type RemoteEntityName =`
                new string:
                `export type RemoteEntityName =
                'app31.statuses' |
                'app31.risks' |`
        7. Create LocalEntity definitions in src/apps/<app_name>/entities folder. Use create_file tool to create a new file for each entity.
            Read src/types/index.ts to understand the meaning of the flags and functions used in the file.
            Example:
                src/apps/app29/entities/incoming_invoices.ts
                    /* eslint-disable camelcase */
                    import { Id, Column, MenuItem, singleControlledAction } from 'src/types'
                    import VuexModuleConstructor from 'src/utils/vuexModuleConstructor/VuexModuleConstructor'
                    import { isInteger, inlineEdit, hideWhenCreatingAndEditing } from 'src/types/columnFlags'
                    import localEntityListInMenuItem from 'src/utils/mainMenuOperations/localEntityListInMenuItem'
                    import { RemoteEntityName } from 'src/types/remoteEntityNames'
                    import { LocalEntityName } from 'src/types/localEntityNames'
                    import showGrandTotalsForSummableColumns from 'src/utils/entityOperations/columns/showGrandTotalsForSummableColumns'
                    import { Vendor } from '../vendors/vendors'

                    export interface IncomingInvoice {
                    id: Id
                    vendor_id: Vendor['id']
                    invoice_date: Date
                    received_on: Date
                    amount: number
                    description: string
                    }

                    type T = IncomingInvoice

                    const controlledActions = singleControlledAction(860)

                    const columns = (): Column<T>[] => {
                    return [
                        { name: 'row_menu', style: 'width:20px', hideWhenCreatingAndEditing, type: 'row_menu', menuItemShortcuts: ['del', 'copy'] },
                        { name: 'id', style: 'width:30px', isInteger, hideWhenCreatingAndEditing },
                        { name: 'vendor_id', style: 'width:30px', references: 'app29.vendors', editable: true },
                        { name: 'invoice_date', style: 'width:30px', inlineEdit },
                        { name: 'received_on', style: 'width:30px', inlineEdit },
                        { name: 'amount', style: 'width:30px', isInteger, inlineEdit },
                        { name: 'description', style: 'width:30px', inlineEdit }
                    ]
                    }

                    const remoteEntityName: RemoteEntityName = 'app29.incoming_invoices'
                    const localEntityName: LocalEntityName = remoteEntityName

                    const localEntity = VuexModuleConstructor({
                    columns,
                    remoteEntityName,
                    apiVersion: 1,
                    controlledActions,
                    pageTitle: 'Incoming invoices'
                    })

                    export default localEntity

                    export const incoming_invoices__menuItem = (): MenuItem => ({
                    label: 'Incoming invoices',
                    icon: { name: 'mdi-keyboard-outline' },
                    prefetch: true,
                    ...localEntityListInMenuItem<T>({
                        localEntityNameProp: localEntityName,
                        ...showGrandTotalsForSummableColumns({ cols: columns() })
                    })
                    })

        8. Create RemoteEntity definitions in src/apps/<app_name>/entities folder. Use create_file tool to create a new file for each entity.
            Ask user schema name of the app. It must start with 'app' and be followed by a number. E.g., `app29`.
            Example:
                src/apps/app29/entities/incoming_invoices.pgsql
                create or replace procedure app29.incoming_invoices__init ()
                language plpgsql
                as $$
                begin

                if not relation_exists('app29.incoming_invoices') then
                    create table app29.incoming_invoices (
                        id int primary key generated always as identity
                        , vendor_id int references app29.vendors(id)
                        , invoice_date date
                        , received_on date
                        , amount numeric
                        , description text
                    );
                end if;


                insert into meta.entities ( name )
                select 'app29.incoming_invoices'
                where not exists ( select 1 from meta.entities where name = 'app29.incoming_invoices' );

                end;
                $$;

                call app29.incoming_invoices__init();

        9. Write to src/apps/<app_name>/config/mastersToFetch.ts the names of the entities that should be fetched from the backend as master data.
            Example:
            src/apps/app29/config/mastersToFetch.ts

            import { LocalEntityName } from 'src/types/localEntityNames'

            const mastersToFetch: LocalEntityName[] = [
                'app29.vendors',
                'app29.customers',
                'app29.vendor_contracts',
                'app29.customer_contracts',
                'app29.incoming_invoices',
                'app29.outgoing_invoices',
                'app29.incoming_payments',
                'app29.outgoing_payments'
            ]

            export default mastersToFetch

        10. Write to src/apps/<app_name>/config/entitiesToRegister.ts the names of the entities that should be registered in the app.
            Example:
            src/apps/app29/config/entitiesToRegister.ts
            /* eslint-disable camelcase */
            import vendors from '../entities/vendors/vendors'
            import vendor_contracts from '../entities/vendor_contracts/vendor_contracts'
            import incoming_invoices from '../entities/incoming_invoices/incoming_invoices'
            import outgoing_invoices from '../entities/outgoing_invoices/outgoing_invoices'
            import outgoing_invoice_lines from '../entities/outgoing_invoices/outgoing_invoice_lines'
            import incoming_payments from '../entities/incoming_payments/incoming_payments'
            import outgoing_payments from '../entities/outgoing_payments/outgoing_payments'
            import incoming_paymanets_rel_outgoing_invoices from '../entities/incoming_paymanets_rel_outgoing_invoices/incoming_paymanets_rel_outgoing_invoices'
            import customers from '../entities/customers/customers'
            import { LocalEntityNameToLocalEntityMap } from 'src/types'

            const vuexModulesToRegister: LocalEntityNameToLocalEntityMap = {
                'app29.vendors': vendors,
                'app29.vendor_contracts': vendor_contracts,
                'app29.incoming_invoices': incoming_invoices,
                'app29.outgoing_invoices': outgoing_invoices,
                'app29.outgoing_invoices__open': outgoing_invoices,
                'app29.outgoing_invoice_lines': outgoing_invoice_lines,
                'app29.incoming_payments': incoming_payments,
                'app29.incoming_payments__unallocated': incoming_payments,
                'app29.outgoing_payments': outgoing_payments,
                'app29.incoming_paymanets_rel_outgoing_invoices': incoming_paymanets_rel_outgoing_invoices,
                'app29.customers': customers
            }

            export default vuexModulesToRegister

        11. Populate src/menus/default.ts with the menu structure, using menu items exported from the entities and menus files.
            Example:
            src/apps/app29/menus/default.ts
            /* eslint-disable camelcase */
            import { MenuItem } from 'src/types'
            import { customers__menuItem } from '../entities/customers/customers'
            import { incoming_invoices__menuItem } from '../entities/incoming_invoices/incoming_invoices'
            import { incoming_paymanets_rel_outgoing_invoices__menuItem } from '../entities/incoming_paymanets_rel_outgoing_invoices/incoming_paymanets_rel_outgoing_invoices'
            import { incoming_payments__menuItem, incoming_payments__unsettled__menuItem } from '../entities/incoming_payments/incoming_payments'
            import { outgoing_invoices__menuItem, outgoing_invoices__open__menuItem } from '../entities/outgoing_invoices/outgoing_invoices'
            import { outgoing_payments__menuItem } from '../entities/outgoing_payments/outgoing_payments'
            import { vendors__menuItem } from '../entities/vendors/vendors'
            import { vendor_contracts__menuItem } from '../entities/vendor_contracts/vendor_contracts'

            const menuItems = (ctx: any): MenuItem[] => {
                return [
                { label: 'Customers', isHeader: true },
                outgoing_invoices__menuItem(),
                outgoing_invoices__open__menuItem(),
                incoming_payments__menuItem(),
                incoming_payments__unsettled__menuItem(),
                incoming_paymanets_rel_outgoing_invoices__menuItem(),
                customers__menuItem(),

                { label: 'Vendors', isHeader: true },
                incoming_invoices__menuItem(),
                outgoing_payments__menuItem(),
                vendor_contracts__menuItem(),
                vendors__menuItem(),

                { label: 'Exceptions', isHeader: true },
                incoming_payments__unsettled__menuItem()
                ]
            }

            export default menuItems

        12. Connect the app to the platform by using sonar_connect_app_to_platform tool.
        """

    sonar_folder_structure = """
      Typical structure of App folder.
      |-- index.ts
      |-- Index.vue
      |-- config <-- config folder contains the configuration files for the app
        |-- mastersToFetch.ts <-- mastersToFetch is used to define the master data that needs to be fetched from the backend. Master data is master in this case because it has special treatment: It is loaded at the beginning in full and is always availabe in the app. It is used to populate dropdowns, etc.
        |-- entitiesToRegister.ts <-- connects the entities to the app. It is used to define which entities are available in the app. Usually, entities defined in folder entities are listed here
      |-- menus <-- menus are used to define the structure of the sidebar. This is the main and only navigation in the app
        |-- default.ts <-- default menu is the main menu of the app. It is used to define the structure of the sidebar
      |-- pages <-- rarely used, because content is mostly displayed in one single big GenericTable component
        |-- Hello.vue
      |-- entities <-- entities are the main building blocks of the app. They are the main data structures that are displayed in the app via the GenericTable component
        |-- customers <-- folder for Entity definition
          |-- customers.pgsql <-- RemoteEntity definition as a SQL query
          |-- customers.ts <-- LocalEntity definition as a strongly types TypeScript object
        |-- customer_contracts
          |-- customer_contracts.pgsql
          |-- customer_contracts.ts
        |-- incoming_invoices
          |-- incoming_invoices.pgsql
          |-- incoming_invoices.ts
        |-- incoming_paymanets_rel_outgoing_invoices
          |-- incoming_paymanets_rel_outgoing_invoices.pgsql
          |-- incoming_paymanets_rel_outgoing_invoices.ts
        |-- incoming_payments
          |-- incoming_payments.pgsql
          |-- incoming_payments.ts
        |-- outgoing_invoices
          |-- OutgoingInvoiceCard.vue <-- Component used for custom editing or viewing card of the entity. It is used in the GenericTable component, and routed from LocalEntity definition
          |-- outgoing_invoices.pgsql
          |-- outgoing_invoices.ts
          |-- outgoing_invoice_lines.ts <-- also LocalEntity definition. Closely related entities, like lines of an invoice, are usually defined in the same
        |-- outgoing_payments
          |-- outgoing_payments.pgsql
          |-- outgoing_payments.ts
        |-- vendors
          |-- vendors.pgsql
          |-- vendors.ts
        |-- vendor_contracts
          |-- vendor_contracts.pgsql
          |-- vendor_contracts.ts
    """  
    
    return SonarPrompts(what_is_sonar=what_is_sonar, sonar_folder_structure=sonar_folder_structure)
  

# endregion: Sonar prompts

# region: Tools
def update_system_prompt(current_iteration=None, max_iterations=None):
    global base_system_prompt, automode_system_prompt
    chain_of_thought_prompt = """
    Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

    Do not reflect on the quality of the returned search results in your response.
    """
    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return base_system_prompt + "\n\n" + automode_system_prompt.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt
    else:
        return base_system_prompt + "\n\n" + chain_of_thought_prompt

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"

def create_file(path, content=""):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)

def generate_and_apply_diff(original_content, new_content, path):
    diff = list(difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    if not diff:
        return "No changes detected."

    try:
        with open(path, 'w') as f:
            f.writelines(new_content)

        diff_text = ''.join(diff)
        highlighted_diff = highlight_diff(diff_text)

        diff_panel = Panel(
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="cyan"
        )

        console.print(diff_panel)

        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        summary = f"Changes applied to {path}:\n"
        summary += f"  Lines added: {added_lines}\n"
        summary += f"  Lines removed: {removed_lines}\n"

        return summary

    except Exception as e:
        error_panel = Panel(
            f"Error: {str(e)}",
            title="Error Applying Changes",
            style="bold red"
        )
        console.print(error_panel)
        return f"Error applying changes: {str(e)}"

def search_file(path, search_pattern):
    try:
        with open(path, 'r') as file:
            content = file.readlines()

        matches = []
        for i, line in enumerate(content, 1):
            if re.search(search_pattern, line):
                matches.append(i)

        return f"Matches found at lines: {matches}"
    except Exception as e:
        return f"Error searching file: {str(e)}"

def edit_file(path, start_line, end_line, new_content):
    try:
        with open(path, 'r') as file:
            content = file.readlines()

        original_content = ''.join(content)

        start_index = start_line - 1
        end_index = end_line

        content[start_index:end_index] = new_content.splitlines(True)

        new_content = ''.join(content)

        diff_result = generate_and_apply_diff(original_content, new_content, path)

        return f"Successfully edited lines {start_line} to {end_line} in {path}\n{diff_result}"
    except Exception as e:
        return f"Error editing file: {str(e)}"

def read_file(path):
    try:
        with open(path, 'rb') as f:
            raw_data = f.read()
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        content = raw_data.decode(encoding)
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path="."):
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def list_files_recursively(path=".", depth=0, max_depth=5, exclude_dirs=['dist', 'node_modules', 'build', 'target', 'debug', 'cache'], exclude_file_extensions=[], max_tokens=19999):
    try:
        files = []
        anthropic = Anthropic()
        total_tokens = 0

        for root, dirs, filenames in os.walk(path):
            current_depth = root[len(path):].count(os.sep)

            if current_depth > max_depth:
                del dirs[:]
                continue

            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for filename in filenames:
                if not any(filename.endswith(ext) for ext in exclude_file_extensions):
                    file_path = os.path.relpath(os.path.join(root, filename), path)
                    file_tokens = anthropic.count_tokens(file_path + "\n")

                    if total_tokens + file_tokens > max_tokens:
                        return "\n".join(files) + "\n...\n(truncated)"

                    files.append(file_path)
                    total_tokens += file_tokens

        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def copy_folder_with_content(src, dest):
    try:
        shutil.copytree(src, dest)
        return f"Folder copied: {src} to {dest}"
    except Exception as e:
        return f"Error copying folder: {str(e)}"

def replace_string_in_file(file_path, old_string, new_string):
    try:
        with open(file_path, 'r') as file:
            filedata = file.read()

        new_filedata = filedata.replace(old_string, new_string)

        with open(file_path, 'w') as file:
            file.write(new_filedata)

        return f"Replaced '{old_string}' with '{new_string}' in {file_path}"
    except Exception as e:
        return f"Error replacing string in file: {str(e)}"

def sonar_connect_app_to_platform(app_id, app_folder):
    ldm_import_location = "src/components/LeftDrawerMenu/index.vue"
    anchor = '// <-- new-ldm-import-goes-here'
    ldm_import_line = f"import ldm{app_id} from 'src/apps/{app_folder}/menus/default'"
    replacement = f"{ldm_import_line}\n{anchor}"
    replace_string_in_file(ldm_import_location, anchor, replacement)

    anchor2 = '// <-- new-ldm-mapping-goes-here'
    replacement2 = f",\n{app_id}: ldm{app_id}{anchor2}"
    replace_string_in_file(ldm_import_location, anchor2, replacement2)

    app_page = "src/components/AppPage/AppPage.vue"
    anchor3 = '// <-- new-app-page-import-goes-here'
    import_line3 = f"import appPage{app_id} from 'src/apps/{app_folder}/Index.vue'"
    replacement3 = f"{import_line3}\n{anchor3}"
    replace_string_in_file(app_page, anchor3, replacement3)

    anchor4 = '// <-- new-app-page-component-goes-here'
    replacement4 = f",\nappPage{app_id}{anchor4}"
    replace_string_in_file(app_page, anchor4, replacement4)

def tavily_search(query):
    try:
        response = tavily.qna_search(query=query, search_depth="advanced")
        return response
    except Exception as e:
        return f"Error performing search: {str(e)}"
# endregion: Tools

sonar_tools = []

tools = sonar_tools + [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_file",
        "description": "Search for a specific pattern in a file and return the line numbers where the pattern is found. Use this to locate specific code or text within a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to search"
                },
                "search_pattern": {
                    "type": "string",
                    "description": "The pattern to search for in the file"
                }
            },
            "required": ["path", "search_pattern"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit a specific range of lines in a file. Use this after using search_file to identify the lines you want to edit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to edit"
                },
                "start_line": {
                    "type": "integer",
                    "description": "The starting line number of the edit"
                },
                "end_line": {
                    "type": "integer",
                    "description": "The ending line number of the edit"
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content to replace the specified lines"
                }
            },
            "required": ["path", "start_line", "end_line", "new_content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. Use this when you need to see the contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)"
                }
            }
        }
    },
    {
        "name": "list_files_recursively",
        "description": "List all files and directories in the specified folder and its subdirectories. Use this when you need to see the contents of a directory and its subdirectories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list recursively (default: current directory)"
                }
            }
        }
    },
    { "name": "copy_folder_with_content",
        "description": "Copy the contents of a folder to a new location. Use this when you need to duplicate a folder and its contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "src": {
                    "type": "string",
                    "description": "The path of the source folder to copy"
                },
                "dest": {
                    "type": "string",
                    "description": "The path of the destination folder where the contents will be copied"
                }
            },
            "required": ["src", "dest"]
        }
    },
    { "name": "replace_string_in_file",
        "description": "Replace a specific string with another string in a file. Use this when you need to update specific content in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the file to modify"
                },
                "old_string": {
                    "type": "string",
                    "description": "The string to replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "The new string to insert"
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }
    },
    {
        "name": "sonar_connect_app_to_platform",
        "description": "Connect the App to the Sonar platform by updating the necessary files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The ID of the App"
                },
                "app_folder": {
                    "type": "string",
                    "description": "The folder name of the App"
                }
            },
            "required": ["app_id", "app_folder"]
        }
    },
    {
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

def execute_tool(tool_name, tool_input):
    try:
        if tool_name == "create_folder":
            return create_folder(tool_input["path"])
        elif tool_name == "create_file":
            return create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "search_file":
            return search_file(tool_input["path"], tool_input["search_pattern"])
        elif tool_name == "edit_file":
            return edit_file(tool_input["path"], tool_input["start_line"], tool_input["end_line"], tool_input["new_content"])
        elif tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "list_files":
            return list_files(tool_input.get("path", "."))
        elif tool_name == "list_files_recursively":
            return list_files_recursively(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            return tavily_search(tool_input["query"])
        elif tool_name == "copy_folder_with_content":
            return copy_folder_with_content(tool_input["src"], tool_input["dest"])
        elif tool_name == "replace_string_in_file":
            return replace_string_in_file(tool_input["file_path"], tool_input["old_string"], tool_input["new_string"])
        elif tool_name == "sonar_connect_app_to_platform":
            return sonar_connect_app_to_platform(tool_input["app_id"], tool_input["app_folder"])
        else:
            return f"Unknown tool: {tool_name}"
    except KeyError as e:
        return f"Error: Missing required parameter {str(e)} for tool {tool_name}"
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def parse_goals(response):
    goals = re.findall(r'Goal \d+: (.+)', response)
    return goals

def execute_goals(goals):
    global automode
    for i, goal in enumerate(goals, 1):
        console.print(Panel(f"Executing Goal {i}: {goal}", title="Goal Execution", style="bold yellow"))
        response, _ = chat_with_claude(f"Continue working on goal: {goal}")
        if CONTINUATION_EXIT_PHRASE in response:
            automode = False
            console.print(Panel("Exiting automode.", title="Automode", style="bold green"))
            break

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode

    current_conversation = []

    if image_path:
        console.print(Panel(f"Processing image at path: {image_path}", title_align="left", title="Image Processing", expand=False, style="yellow"))
        image_base64 = encode_image_to_base64(image_path)

        if image_base64.startswith("Error"):
            console.print(Panel(f"Error encoding image: {image_base64}", title="Error", style="bold red"))
            return "I'm sorry, there was an error processing the image. Please try again.", False

        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": f"User input for image: {user_input}"
                }
            ]
        }
        current_conversation.append(image_message)
        console.print(Panel("Image message added to conversation history", title_align="left", title="Image Added", style="green"))
    else:
        current_conversation.append({"role": "user", "content": user_input})

    messages = conversation_history + current_conversation

    try:
        response = client.messages.create(
            model=MAINMODEL,
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
    except APIStatusError as e:
        if e.status_code == 429:
            console.print(Panel("Rate limit exceeded. Retrying after a short delay...", title="API Error", style="bold yellow"))
            time.sleep(5)
            return chat_with_claude(user_input, image_path, current_iteration, max_iterations)
        else:
            console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
            return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    except APIError as e:
        console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False

    assistant_response = ""
    exit_continuation = False
    tool_uses = []

    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_uses.append(content_block)

    console.print(Panel(Markdown(assistant_response), title="Claude's Response", title_align="left", expand=False))

    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="green"))
        console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="green"))

        try:
            result = execute_tool(tool_name, tool_input)
            console.print(Panel(result, title_align="left", title="Tool Result", style="green"))
        except Exception as e:
            result = f"Error executing tool: {str(e)}"
            console.print(Panel(result, title="Tool Execution Error", style="bold red"))

        current_conversation.append({
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": tool_input
                }
            ]
        })

        current_conversation.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result
                }
            ]
        })

        messages = conversation_history + current_conversation

        try:
            tool_response = client.messages.create(
                model=TOOLCHECKERMODEL,
                max_tokens=4000,
                system=update_system_prompt(current_iteration, max_iterations),
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )

            tool_checker_response = ""
            for tool_content_block in tool_response.content:
                if tool_content_block.type == "text":
                    tool_checker_response += tool_content_block.text
            console.print(Panel(Markdown(tool_checker_response), title="Claude's Response to Tool Result", title_align="left"))
            assistant_response += "\n\n" + tool_checker_response
        except APIError as e:
            error_message = f"Error in tool response: {str(e)}"
            console.print(Panel(error_message, title="Error", style="bold red"))
            assistant_response += f"\n\n{error_message}"

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    conversation_history = messages + [{"role": "assistant", "content": assistant_response}]

    return assistant_response, exit_continuation

def main():
    global automode, conversation_history
    console.print(Panel("Welcome to the Claude-3-Sonnet Engineer Chat with Image Support!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")

    while True:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
            break

        if user_input.lower() == 'image':
            image_path = console.input("[bold cyan]Drag and drop your image here, then press enter:[/bold cyan] ").strip().replace("'", "")

            if os.path.isfile(image_path):
                user_input = console.input("[bold cyan]You (prompt for image):[/bold cyan] ")
                response, _ = chat_with_claude(user_input, image_path)
            else:
                console.print(Panel("Invalid image path. Please try again.", title="Error", style="bold red"))
                continue
        elif user_input.lower().startswith('automode'):
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS

                automode = True
                console.print(Panel(f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.", title_align="left", title="Automode", style="bold yellow"))
                console.print(Panel("Press Ctrl+C at any time to exit the automode loop.", style="bold yellow"))
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(Panel("Automode completed.", title_align="left", title="Automode", style="green"))
                            automode = False
                        else:
                            console.print(Panel(f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode. ", title_align="left", title="Automode", style="yellow"))
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(Panel("Max iterations reached. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                            automode = False
                except KeyboardInterrupt:
                    console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                    automode = False
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                automode = False
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})

            console.print(Panel("Exited automode. Returning to regular chat.", style="green"))
        else:
            response, _ = chat_with_claude(user_input)

if __name__ == "__main__":
    main()
