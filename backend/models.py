from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
db = client['buddy_matcher']

# Collections
users = db['users']
profiles = db['profiles']
activities = db['activities']
actions = db['actions']
reviews = db['reviews']

# Create indexes
users.create_index('email', unique=True)
profiles.create_index('user_id', unique=True)
actions.create_index(['from_uid', 'to_uid'], unique=True)

# Data models structure
"""
users:
- _id: ObjectId
- email: String (unique)
- password: String (hashed)
- created_at: Date

profiles:
- _id: ObjectId
- user_id: ObjectId (ref to users)
- gender: String
- mbti: String
- occupation: String
- personality: String
- location: Object
  - city: String
  - district: String
- privacy_settings: Object
  - age_visible: Boolean
  - occupation_visible: Boolean
- reputation: Number (0-5)
- ai_tags: Array[String]
- created_at: Date
- updated_at: Date

activities:
- _id: ObjectId
- user_id: ObjectId (ref to users)
- title: String
- content: String
- category: String
- time: Date
- location: Object
  - city: String
  - district: String
- status: String (ongoing, paused, completed, expired)
- participants: Array[ObjectId]
- created_at: Date
- updated_at: Date

actions:
- _id: ObjectId
- from_uid: ObjectId (ref to users)
- to_uid: ObjectId (ref to users)
- action: String (like, pass)
- created_at: Date

reviews:
- _id: ObjectId
- from_uid: ObjectId (ref to users)
- to_uid: ObjectId (ref to users)
- activity_id: ObjectId (ref to activities)
- rating: Number (1-5)
- comment: String
- created_at: Date
"""
