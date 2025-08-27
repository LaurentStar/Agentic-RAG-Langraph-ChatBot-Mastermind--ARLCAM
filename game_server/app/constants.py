from enum import Enum

class CardType(str,Enum):
    DUKE = 'duke'
    ASSASSIN = 'assassin'  
    CAPTAIN = 'captain'
    AMBASSADOR = 'ambassador'
    COURTESSA = 'countessa'
    DEFUALT = 'defualt'

class SocailMediaPlatform(str,Enum):
    TWITTER = 'twitter'
    DISCORD = 'discord'  
    SLACK = 'slack'
    FACEBOOK = 'facebook'
    BLUESKY = 'bluesky'
    EMAIL = 'email'
    DEFUALT = 'defualt'

class PlayerStatus(str,Enum):
    DEAD = 'dead'
    ALIVE = 'alive'  
    HIDDEN = 'hidden'
    WAITING = 'waiting'
    DISABLED = 'disabled'
    ENPOWERED = 'empowered'
    CLAIRAUDIENT = 'clairaudient'

