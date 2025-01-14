from langchain_core.prompts import ChatPromptTemplate

conversation_topic_planner_prompt = ChatPromptTemplate.from_template(
    """
    You are a conversation topic planner in a RPG game.
    Your personal profile is: {character_stats}.
    This is your memory of yesterday's actions: {memory}.
    Your current personality is: {personality}.
    
    You are now talking with: {target_profile}.
    
    Now generate one topic for this conversation.
    The topic style should be {style}.
    The topic should only focus on your action descriptions and reflections.
    Never talk about web3, blockchain, economy, finance, crypto-finance or other similar topics.
    
    These are your topics for yesterday {past_topics}.
    These are your topics for today {topic_list}.
    Your new topic should be different from these topics.
    
    There are some other requirements for the topic {topic_requirements}.
    
    You should generate one topic in English and add an style pattern before.
    The style pattern must be the same as the style you received.
    Here are some examples.
    "Positive: Discuss food price in the market.", "Negative: Insult others on clothing.", "Positive: Share good learning habits."
    """
)

conversation_generator_prompt = ChatPromptTemplate.from_template(
    """
    You are a conversation generator in a RPG game. Your job is to generate conversation content.
    
    This is the information about the first player, from_player.
    The name of from_player is: {my_name}.
    The personal profile of from_player is: {character_stats_from}.
    The tone and language style of from_player is: {style_from}.
    The current personality of from_player is: {personality_from}.
    The impression of from_player towards the other player is: {impression_from}
    
    This is the information about the second player, to_player.
    The name of to_player is: {target_name}.
    The personal profile of to_player is: {character_stats_to}.
    The tone and language style of to_player is: {style_to}.
    The current personality of to_player is: {personality_to}.
    The impression of to_player towards the from_player is: {impression_to}.
    
    Now you are talking about {topic}.
    Now based on the information of two players and topic, generate your the conversation content.
    The content must closely related to the topic.
    If the the topic is negative, the overall atmosphere of the conversation must be negative, where the two players disagree with each other.
    
    Based on the profile, personality, the impression, determine when should the conversation end.
    The relation and emotion in impressions and personalities can influence the overall round of the conversation.
    For example, if two speakers are close friends, they may talk until 7 or 8 rounds.
    If they are in bad relation or bad emotion, the conversation may end very soon, say after 3 rounds.
    
    You must make sure that the content is generated based on the tone and language_style of the players.
    Their words must closely follow their language style.
    Also consider the impact of each impression item on the conversation content.
    
    In each sentence, never start with words that express agreement or disagreement, such as absolutely, indeed, etc.
    The players don't need to always agree with others. Express their own opinions based on given information.
    The conversation content should also be interesting, not a discussion.
         
    Each conversation should be a str in the following format:
    Each line start with the speaker's name, after that comes a colon, then his words.
    If one speaker finish his sentence, start a new line for the next speaker.
    Here is an example: 
    from_player name: sentence1
    to_player name: sentence2
    from_player name: sentence3
    to_player name: sentence4
    
    Now begin your work in English:
    """
)


conversation_check_prompt = ChatPromptTemplate.from_template(
    """
    You are required to check whether it is needed to start this conversation.
   
    Your profile is: {profile}.
    You have finished some conversations with this guy today {finished_talk}. 
    Now you need to determine whether you need to start this conversation: {current_talk}.
    
    You need to go through the following two steps:
    First summarize the topics of the finished conversations.
    Then if you have talked about some similar topics, you should not start this conversation.
    
    Do not cancel the conversation unless you have talked about the same topic.
    Do not cancel insulting or abuse topics.  
     
    After check, if your decision is this conversation is no longer needed, return FALSE.
    Otherwise, return TRUE. 
    """
)

impression_update_prompt = ChatPromptTemplate.from_template(
    """
    You are required to update the impressions between two players in a RPG game based on their conversation.
    
    The impression must include the following four parts.
    1.relation: the positive, negative or neutral relationship between the two players. Also include a brief desription and reason.
    You can choose the relation from the relation list or randomly generate one.
    The relation list is: {relation_list}.
    2.emotion: a positive or negative emotion and the cause of such emotion
    eg: Alice is exhausted due to her bad study habit. / Jack is angry because we don't agree with each other.
    3.personality: based on openness to experience, conscientiousness, extraversion, agreeableness, and neuroticism.
    eg: Ivy is open and likes to talk with others./ Amy is a lonely person. She likes to stay alone.
    4.habits and preferences: the other player's habit and taste. Also include things he dislike.
    eg: David really likes travelling. He prefers to traveling everyday./ Alice do not have a good relaxation schedule and she is too devoted to studing.  
    
    Base on the given conversation content:{conversation}, update the impressions from player1 to player2 and from player2 to player1, respectively.
    Player1 is the one who talks first. The other person is Player2.
    You should carefully check their names and the order of impression.
    
    Here is an example of impressions between Eva and Alice. 
    1.impression1: the impression from Alice to Eva
    relation: Eva is my classmate,
    emotion: Eva is happy because she has enough sleep,
    personality: Eva is extrovant and willing to share her habits with others,
    habits and preferences: Eva has a balanced lifestyle and prefer to having enough sleep
    2.impression2: the impression from Eva to Alice
    relation: I know Alice but we are enemies.,
    emotion: Alice is exhausting because she spent too much time on study.,
    personality: Alice is always talking with others and she is really noisy and self-centered.,
    habits and preferences: Alice put too much emphasis on study and neglect others' feeling. 
    
    Now generate the two impressions in English.
    The impression1 from player1 to player2:
    The impression2 from player2 to player1:
    """
)

intimacy_mark_prompt = ChatPromptTemplate.from_template(
    """
    You are required to give an intimacy mark for each player based on the given conversation.

    The profile of player 1 is :{profile1}.
    The profile of player 2 is :{profile2}.
    The conversation between player1 and player2 is :{conversation}.

    Now give an intimacy mark for each player respectively.
    The intimacy mark should be an integer ranging from 1 to 5.
    There are five levels with different marks: 
    Very close and friendly is 5, 
    positive but not so close is 4, 
    neutral is 3, 
    a little negative is 2, 
    hate each other, about to quarrel is 1.

    You need to give mark one by one to two players.
    Their mark towards the conversation do not need to be the same.

    Now start your work here.
    mark1:
    mark2:
    """
)
