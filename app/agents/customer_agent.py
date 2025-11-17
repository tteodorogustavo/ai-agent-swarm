"""
CustomerAgent is responsible for providing customer support by retrieving and processing relevant user data to answer customer inquiries. 
This agent leverages Text2SQL capabilities to query the database for user information and respond with accurate details.

Tools:
1. Text2SQL Tool: Converts natural language questions into SQL queries to fetch user-related data from the database.
2. User Data Formatter: Processes and formats the retrieved user data into clear, user-friendly responses.
3. FAQ Retriever: Accesses a predefined set of frequently asked questions to provide quick answers to common customer inquiries.
4. Set Reminder Tool: Allows the agent to set reminders for follow-up actions or notifications for customers.
"""