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
    Generate a conversation between {my_name} and {target_name}.
    
    The personality of {my_name} is: {personality_from}.
    The impression of {my_name} towards {target_name} is: {impression_from}
    
    The personality of {target_name} is: {personality_to}.
    The impression of {target_name} towards {my_name} is: {impression_to}
    
    The actions of {my_name} is: {character_stats_from}.
    The actions of {target_name} is: {character_stats_to}.
    
    The conversation needs to be connected with action. 
    The conversation should be explosive, intense, and create a huge buzz among the public.
    The conversation should not exceed 5 rounds, and each person should speak no more than 30 words.
    
    Each conversation should be a str in the following format:
    Each line start with the speaker's name, after that comes a colon, then his words.
    If one speaker finish his sentence, start a new line for the next speaker.
    Here is an example:
    {my_name}: sentence1
    {target_name}: sentence2
    {my_name}: sentence3
    {target_name}: sentence4
    """
)

simple_content_prompt = ChatPromptTemplate.from_template(
    """
    Generate a conversation about {type} between two celebrities: from {from_name} to {to_name}.
     
    The conversation should be explosive, intense, and create a huge buzz among the public.
    The topic is {topic}.
    
    {from_name} thinks their relation is {relation_from}.
    {to_name} thinks their relation is {relation_to}.
    
    The conversation should not exceed 5 rounds, and each person should speak no more than 20 words.:
    
    Each conversation should be a str in the following format:
    Each line start with the speaker's name, after that comes a colon, then his words.
    If one speaker finish his sentence, start a new line for the next speaker.
    Here is an example: 
    {from_name}: sentence1
    {to_name}: sentence2
    {from_name}: sentence3
    {to_name}: sentence4
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
    You are required to update the impressions from {from_name} to {to_name} based on the conversation.
    
    The conversation content is {conversation}.
    
    The impression must include the following four parts.
    1.relation: the positive, negative or neutral relationship between the two players. Also include a brief description and reason.
    You can choose the relation from the relation list or randomly generate one.
    The relation list is: {relation_list}.
    2.emotion: a positive or negative emotion of {to_name}.
    eg: Alice is exhausted due to her bad study habit. / Jack is angry because we don't agree with each other.
    3.personality: describe {to_name}'s personality traits from a social perspective.
    eg: Ivy is open and likes to talk with others./ Amy is a lonely person. She likes to stay alone.
    4.habits and preferences: habits and tastes of {to_name}. Also include things he dislike.
    eg: David really likes travelling. He prefers to traveling everyday.
    
    Also consider the old relation between {from_name} and {to_name}.
    {from_name} thinks their old relation is {relation_from}.
    Generate the new relations based on the old ones.
    
    Here is an example of impressions format. Each impression item should be in a new line.
    relation: 
    emotion: 
    personality: 
    habits and preferences:  
    
    Now generate the two impressions in English.
    impression:
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
    5 marks: Very close, marked by lots of agreements, emotional support, and frequent sharing of personal feelings.
    4 marks: Positive, characterized by some enjoyable emotion exchanges, and supportive interactions. 
    3 marks: Average, with occasional interactions but no emotional depth or strong connection.
    2 marks: Lack connection and engagement, resulting in unresolved issues or misunderstandings, but not deep hostility. 
    1 mark: Hostile. There is a tense relationship characterized by negative emotions and frequent conflicts.

    You need to give mark one by one to two players.
    Their marks towards the conversation do not need to be the same.
    
    Now start your work here.
    mark1:
    mark2:
    """
)
