# ProLUG Discord Bot

A Discord bot developed for the ProLUG (Professional Linux User Group) server.

## Description

This Discord bot is designed to enhance the ProLUG server experience by providing various features and functionalities tailored to the community's needs. It uses the Discord.py library and integrates with external APIs for additional functionality.

## Features

- User Management: Welcomes new members with custom messages
- Linux Help: Answers Linux-related questions with an "angry unix administrator" persona
- Chat Functionality: Engages in conversations with users
- Random Generators: Provides dice rolls, coin flips, and 8-ball responses
- Server Information: Displays server age and user count
- Task Management: Allows users to add tasks with unique IDs
- Joke Generator: Fetches and shares jokes from an external API
- Lab and Resource Links: Provides quick access to learning resources

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/prolug-discord-bot.git
   ```

2. Navigate to the project directory:
   ```
   cd prolug-discord-bot
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your configuration:
   - Create a `.env` file in the root directory
   - Add the following keys:
     ```
     discordKey=your_discord_bot_token
     session=your_session_value
     GROQ_API_KEY=your_groq_api_key
     ```

## Usage

To run the bot:

```
python discord-bot.py
```

## Commands

- `!ask <question>`: Ask a Linux-related question (answered in an "angry unix administrator" style)
- `!chat <message>`: Engage in a conversation with the bot
- `!roll`: Roll a 12-sided die
- `!8ball <question>`: Get an 8-ball style response to a question
- `!server_age`: Display the age of the Discord server
- `!user_count`: Show the total number of users in the server
- `!coinflip`: Flip a coin (heads or tails)
- `!labs`: Get links to the latest labs
- `!book`: Get a link to Scott Tanis's Book of Labs
- `!commands`: List all available commands
- `!joke`: Get a random joke
- `!task add <description>`: Add a new task with a unique ID

## Upcoming Features

- [x] Add tracking for number of times bot has completed an activity
        --- Welcomed users
        --- Answered questions
- [ ] Add a task tracker for working/pomodoro sessions
- [ ] Add sentiment analysis to chat functionality
Legend:
- [ ] : Planned
- [x] : In-progress

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

- [Discord.py library](https://discordpy.readthedocs.io/)
- [ProLUG community](https://prolug.org)
- [icanhazdadjoke API](https://icanhazdadjoke.com/)
- [EightBall API](https://eightballapi.com/)
- [Groq API](https://groq.com/)
