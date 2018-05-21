# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import adal
from random import Random
import traceback
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.keyvault.models import AccessPolicyEntry, VaultProperties, Sku, KeyPermissions, SecretPermissions, \
    CertificatePermissions, StoragePermissions, Permissions, VaultCreateOrUpdateParameters
try:
    import urllib.parse as urlutil
except:
    import urllib as urlutil

SECRET_PERMISSIONS_ALL = [perm.value for perm in SecretPermissions]
KEY_PERMISSIONS_ALL = [perm.value for perm in KeyPermissions]
CERTIFICATE_PERMISSIONS_ALL = [perm.value for perm in CertificatePermissions]
STORAGE_PERMISSIONS_ALL = [perm.value for perm in StoragePermissions]

_rand = Random()

def get_name(base, delimiter='-'):
    """
    randomly builds a unique name for an entity beginning with the specified base 
    :param base: the prefix for the generated name
    :return: a random unique name
    """
    name = '{}{}{}{}{}'.format(base, delimiter, _rand.choice(adjectives), delimiter, _rand.choice(nouns))
    if len(name) < 22:
        name += delimiter
        for i in range(min(5, 23 - len(name))):
            name += str(_rand.choice(range(10)))
    return name


def keyvaultsample(f):
    """
    decorator function for marking key vault sample methods
    """
    def wrapper(self):
        try:
            print('--------------------------------------------------------------------')
            print('RUNNING: {}'.format(f.__name__))
            print('--------------------------------------------------------------------')
            self.setup_sample()
            f(self)
        except Exception as e:
            print('ERROR: running sample failed with raised exception:')
            traceback.print_exception(type(e), e, getattr(e, '__traceback__', None))
            raise e
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    wrapper.kv_sample = True
    return wrapper


class SampleConfig(object):
    """
    Configuration settings for use in Key Vault sample code.  Users wishing to run this sample can either set these
    values as environment values or simply update the hard-coded values below

    :ivar subscription_id: Azure subscription id for the user intending to run the sample
    :vartype subscription_id: str

    :ivar client_id: Azure Active Directory AppID of the Service Principle to run the sample
    :vartype client_id: str

    :ivar client_oid: Azure Active Directory Object ID of the Service Principal to run the sample
    :vartype client_oid: str

    :ivar tenant_id: Azure Active Directory tenant id of the user intending to run the sample
    :vartype tenant_id: str

    :ivar client_secret: Azure Active Directory Application Key to run the sample
    :vartype client_secret: str

    :ivar location: Azure regional location on which to execute the sample
    :vartype location: str

    :ivar group_name: Azure resource group on which to execute the sample
    :vartype group_name: str
    """

    def __init__(self):
        # get credential information from the environment or replace the dummy values with your client credentials
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID', None)
        self.tenant_id = os.getenv('AZURE_TENANT_ID', None)
        self.client_id = os.getenv('AZURE_CLIENT_ID', None)
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET', None)
        self.client_oid = os.getenv('AZURE_CLIENT_OID', None)
        self.location = os.getenv('AZURE_LOCATION', None)
        self.group_name = os.getenv('AZURE_RESOURCE_GROUP', 'azure-key-vault-samples')
        self.storage_account_name = os.getenv('AZURE_STORAGE_NAME', None)
        self.vault_name = os.getenv('AZURE_VAULT_NAME', None)
        self.mgmt_client_creds = None
        self.vault = None
        self.auth_context = None


class KeyVaultSampleBase(object):
    """
    Base class for Key Vault samples, provides common functionality needed across Key Vault sample code
    """
    _setup_complete = False

    def __init__(self, config=None):
        self.config = config or SampleConfig()
        self.setup_sample()

    @property
    def mgmt_client_creds(self):
        if not self.config.mgmt_client_creds:
            self.config.mgmt_client_creds = self.create_client_creds()
        return self.config.mgmt_client_creds

    def create_client_creds(self):
        return ServicePrincipalCredentials(client_id=self.config.client_id,
                                           secret=self.config.client_secret,
                                           tenant=self.config.tenant_id)

    @property
    def sample_vault_url(self):
        return self.config.vault.properties.vault_uri if self.config.vault else None

    def setup_sample(self):
        """
        Provides common setup for Key Vault samples, such as creating rest clients, creating a sample resource group
        if needed, and ensuring proper access for the service principal.
         
        :return: None 
        """

        if not KeyVaultSampleBase._setup_complete:

            self.config.auth_context = adal.AuthenticationContext('https://login.microsoftonline.com/%s' % self.config.tenant_id)

            resource_mgmt_client = ResourceManagementClient(self.mgmt_client_creds, self.config.subscription_id)

            # ensure the service principle has key vault and storage as valid providers
            resource_mgmt_client.providers.register('Microsoft.KeyVault')
            resource_mgmt_client.providers.register('Microsoft.Storage')

            # ensure the intended resource group exists
            resource_mgmt_client.resource_groups.create_or_update(resource_group_name=self.config.group_name,
                                                                  parameters={'location': self.config.location})
            KeyVaultSampleBase._setup_complete = True

    def grant_access_to_sample_vault(self, vault, oid):

        keyvault_mgmt_client = KeyVaultManagementClient(credentials=self.mgmt_client_creds,
                                                        subscription_id=self.config.subscription_id)

        # setup vault permissions for the access policy for the oid
        permissions = Permissions(keys=KEY_PERMISSIONS_ALL,
                                  secrets=SECRET_PERMISSIONS_ALL,
                                  certificates=CERTIFICATE_PERMISSIONS_ALL,
                                  storage=STORAGE_PERMISSIONS_ALL)

        policy = AccessPolicyEntry(tenant_id=self.config.tenant_id,
                                   object_id=oid,
                                   permissions=permissions)

        vault.properties.access_policies.append(policy)
        return keyvault_mgmt_client.vaults.create_or_update(resource_group_name=self.config.group_name, 
                                                            vault_name=vault.name, 
                                                            parameters=vault).result()

    def get_sample_vault(self):
        """
        Creates a new key vault with a unique name, granting full permissions to the current credentials
        :return: a newly created key vault
        :rtype: :class:`Vault <azure.keyvault.generated.models.Vault>`
        """

        if not self.config.vault:

            keyvault_mgmt_client = KeyVaultManagementClient(self.mgmt_client_creds, self.config.subscription_id)

            if self.config.vault_name:
                vault = keyvault_mgmt_client.vaults.get(resource_group_name=self.config.group_name,
                                                        vault_name=self.config.vault_name)
            else:
                vault_name = get_name('vault')

                # setup vault permissions for the access policy for the sample service principle
                permissions = Permissions(keys=KEY_PERMISSIONS_ALL,
                                          secrets=SECRET_PERMISSIONS_ALL,
                                          certificates=CERTIFICATE_PERMISSIONS_ALL,
                                          storage=STORAGE_PERMISSIONS_ALL)

                policy = AccessPolicyEntry(tenant_id=self.config.tenant_id,
                                           object_id=self.config.client_oid,
                                           permissions=permissions)

                properties = VaultProperties(tenant_id=self.config.tenant_id,
                                             sku=Sku(name='standard'),
                                             access_policies=[policy])

                parameters = VaultCreateOrUpdateParameters(location=self.config.location,
                                                           properties=properties)
                parameters.properties.enabled_for_deployment = True
                parameters.properties.enabled_for_disk_encryption = True
                parameters.properties.enabled_for_template_deployment = True

                print('creating vault {}'.format(vault_name))

                vault = keyvault_mgmt_client.vaults.create_or_update(resource_group_name=self.config.group_name,
                                                                     vault_name=vault_name,
                                                                     parameters=parameters).result()
            self.config.vault = vault
        return self.config.vault


adjectives = ['able', 'acid', 'adept', 'aged', 'agile', 'ajar', 'alert', 'alive', 'all', 'ample',
              'angry', 'antsy', 'any', 'apt', 'arid', 'awake', 'aware', 'back', 'bad', 'baggy',
              'bare', 'basic', 'batty', 'beefy', 'bent', 'best', 'big', 'black', 'bland', 'blank',
              'bleak', 'blind', 'blond', 'blue', 'bogus', 'bold', 'bony', 'bossy', 'both', 'bowed',
              'brave', 'brief', 'brisk', 'brown', 'bulky', 'bumpy', 'burly', 'busy', 'cagey', 'calm',
              'cheap', 'chief', 'clean', 'close', 'cold', 'cool', 'corny', 'crazy', 'crisp', 'cruel',
              'curvy', 'cut', 'cute', 'damp', 'dark', 'dead', 'dear', 'deep', 'dense', 'dim',
              'dirty', 'dizzy', 'dopey', 'drab', 'dry', 'dual', 'dull', 'dull', 'each', 'eager',
              'early', 'easy', 'elite', 'empty', 'equal', 'even', 'every', 'evil', 'fair', 'fake',
              'far', 'fast', 'fat', 'few', 'fine', 'firm', 'five', 'flat', 'fond', 'four',
              'free', 'full', 'fuzzy', 'gamy', 'glib', 'glum', 'good', 'gray', 'grey', 'grim',
              'half', 'half', 'hard', 'high', 'hot', 'huge', 'hurt', 'icky', 'icy', 'ideal',
              'ideal', 'idle', 'ill', 'itchy', 'jaded', 'joint', 'juicy', 'jumbo', 'jumpy', 'jumpy',
              'keen', 'key', 'kind', 'known', 'kooky', 'kosher', 'lame', 'lame', 'lanky', 'large',
              'last', 'late', 'lazy', 'leafy', 'lean', 'left', 'legal', 'lewd', 'light', 'like',
              'limp', 'lined', 'live', 'livid', 'lone', 'long', 'loose', 'lost', 'loud', 'low',
              'loyal', 'lumpy', 'lush', 'mad', 'major', 'male', 'many', 'mealy', 'mean', 'meaty',
              'meek', 'mere', 'merry', 'messy', 'mild', 'milky', 'minor', 'minty', 'misty', 'mixed',
              'moist', 'moody', 'moral', 'muddy', 'murky', 'mushy', 'musty', 'mute', 'muted', 'naive',
              'nasty', 'near', 'neat', 'new', 'next', 'nice', 'nice', 'nine', 'nippy', 'nosy',
              'noted', 'novel', 'null', 'numb', 'nutty', 'obese', 'odd', 'oily', 'old', 'one',
              'only', 'open', 'other', 'our', 'oval', 'pale', 'past', 'perky', 'pesky', 'petty',
              'phony', 'pink', 'plump', 'plush', 'poor', 'posh', 'prime', 'prize', 'proud', 'puny',
              'pure', 'pushy', 'pushy', 'quick', 'quiet', 'rainy', 'rapid', 'rare', 'rash', 'raw',
              'ready', 'real', 'red', 'regal', 'rich', 'right', 'rigid', 'ripe', 'rosy', 'rough',
              'rowdy', 'rude', 'runny', 'sad', 'safe', 'salty', 'same', 'sandy', 'sane', 'scaly',
              'shady', 'shaky', 'sharp', 'shiny', 'short', 'showy', 'shut', 'shy', 'sick', 'silky',
              'six', 'slim', 'slimy', 'slow', 'small', 'smart', 'smug', 'soft', 'solid', 'some',
              'sore', 'soupy', 'sour', 'sour', 'spicy', 'spiky', 'spry', 'staid', 'stale', 'stark',
              'steel', 'steep', 'stiff', 'stout', 'sunny', 'super', 'sweet', 'swift', 'tall', 'tame',
              'tan', 'tart', 'tasty', 'taut', 'teeny', 'ten', 'tepid', 'testy', 'that', 'these',
              'thick', 'thin', 'third', 'this', 'those', 'tidy', 'tiny', 'torn', 'total', 'tough',
              'trim', 'true', 'tubby', 'twin', 'two', 'ugly', 'unfit', 'upset', 'urban', 'used',
              'used', 'utter', 'vague', 'vain', 'valid', 'vapid', 'vast', 'vexed', 'vital', 'vivid',
              'wacky', 'wan', 'warm', 'wary', 'wavy', 'weak', 'weary', 'wee', 'weepy', 'weird',
              'wet', 'which', 'white', 'whole', 'wide', 'wild', 'windy', 'wiry', 'wise', 'witty',
              'woozy', 'wordy', 'worn', 'worse', 'worst', 'wrong', 'wry', 'yummy', 'zany', 'zesty',
              'zonked']

nouns = ['abroad', 'abuse', 'access', 'act', 'action', 'active', 'actor', 'adult', 'advice', 'affair',
         'affect', 'age', 'agency', 'agent', 'air', 'alarm', 'amount', 'anger', 'angle', 'animal',
         'annual', 'answer', 'appeal', 'apple', 'area', 'arm', 'army', 'art', 'aside', 'ask',
         'aspect', 'assist', 'attack', 'author', 'award', 'baby', 'back', 'bad', 'bag', 'bake',
         'ball', 'band', 'bank', 'bar', 'base', 'basis', 'basket', 'bat', 'bath', 'battle',
         'beach', 'bear', 'beat', 'bed', 'beer', 'being', 'bell', 'belt', 'bench', 'bend',
         'bet', 'beyond', 'bid', 'big', 'bike', 'bill', 'bird', 'birth', 'bit', 'bite',
         'bitter', 'black', 'blame', 'blank', 'blind', 'block', 'blood', 'blow', 'blue', 'board',
         'boat', 'body', 'bone', 'bonus', 'book', 'boot', 'border', 'boss', 'bother', 'bottle',
         'bottom', 'bowl', 'box', 'boy', 'brain', 'branch', 'brave', 'bread', 'break', 'breast',
         'breath', 'brick', 'bridge', 'brief', 'broad', 'brown', 'brush', 'buddy', 'budget', 'bug',
         'bunch', 'burn', 'bus', 'button', 'buy', 'buyer', 'cable', 'cake', 'call', 'calm',
         'camera', 'camp', 'can', 'cancel', 'cancer', 'candle', 'candy', 'cap', 'car', 'card',
         'care', 'career', 'carpet', 'carry', 'case', 'cash', 'cat', 'catch', 'cause', 'cell',
         'chain', 'chair', 'chance', 'change', 'charge', 'chart', 'check', 'cheek', 'chest', 'child',
         'chip', 'choice', 'church', 'city', 'claim', 'class', 'clerk', 'click', 'client', 'clock',
         'closet', 'cloud', 'club', 'clue', 'coach', 'coast', 'coat', 'code', 'coffee', 'cold',
         'collar', 'common', 'cook', 'cookie', 'copy', 'corner', 'cost', 'count', 'county', 'couple',
         'course', 'court', 'cousin', 'cover', 'cow', 'crack', 'craft', 'crash', 'crazy', 'cream',
         'credit', 'crew', 'cross', 'cry', 'cup', 'curve', 'cut', 'cycle', 'dad', 'damage',
         'dance', 'dare', 'dark', 'data', 'date', 'day', 'dead', 'deal', 'dealer', 'dear',
         'death', 'debate', 'debt', 'deep', 'degree', 'delay', 'demand', 'depth', 'design', 'desire',
         'desk', 'detail', 'device', 'devil', 'diet', 'dig', 'dinner', 'dirt', 'dish', 'disk',
         'divide', 'doctor', 'dog', 'door', 'dot', 'double', 'doubt', 'draft', 'drag', 'drama',
         'draw', 'drawer', 'dream', 'dress', 'drink', 'drive', 'driver', 'drop', 'drunk', 'due',
         'dump', 'dust', 'duty', 'ear', 'earth', 'ease', 'east', 'eat', 'edge', 'editor',
         'effect', 'effort', 'egg', 'employ', 'end', 'energy', 'engine', 'entry', 'equal', 'error',
         'escape', 'essay', 'estate', 'event', 'exam', 'excuse', 'exit', 'expert', 'extent', 'eye',
         'face', 'fact', 'factor', 'fail', 'fall', 'family', 'fan', 'farm', 'farmer', 'fat',
         'father', 'fault', 'fear', 'fee', 'feed', 'feel', 'female', 'few', 'field', 'fight',
         'figure', 'file', 'fill', 'film', 'final', 'finger', 'finish', 'fire', 'fish', 'fix',
         'flight', 'floor', 'flow', 'flower', 'fly', 'focus', 'fold', 'food', 'foot', 'force',
         'form', 'formal', 'frame', 'friend', 'front', 'fruit', 'fuel', 'fun', 'funny', 'future',
         'gain', 'game', 'gap', 'garage', 'garden', 'gas', 'gate', 'gather', 'gear', 'gene',
         'gift', 'girl', 'give', 'glad', 'glass', 'glove', 'goal', 'god', 'gold', 'golf',
         'good', 'grab', 'grade', 'grand', 'grass', 'great', 'green', 'ground', 'group', 'growth',
         'guard', 'guess', 'guest', 'guide', 'guitar', 'guy', 'habit', 'hair', 'half', 'hall',
         'hand', 'handle', 'hang', 'harm', 'hat', 'hate', 'head', 'health', 'heart', 'heat',
         'heavy', 'height', 'hell', 'hello', 'help', 'hide', 'high', 'hire', 'hit', 'hold',
         'hole', 'home', 'honey', 'hook', 'hope', 'horror', 'horse', 'host', 'hotel', 'hour',
         'house', 'human', 'hunt', 'hurry', 'hurt', 'ice', 'idea', 'ideal', 'image', 'impact',
         'income', 'injury', 'insect', 'inside', 'invite', 'iron', 'island', 'issue', 'item', 'jacket',
         'job', 'join', 'joint', 'joke', 'judge', 'juice', 'jump', 'junior', 'jury', 'keep',
         'key', 'kick', 'kid', 'kill', 'kind', 'king', 'kiss', 'knee', 'knife', 'lab',
         'lack', 'ladder', 'lady', 'lake', 'land', 'laugh', 'law', 'lawyer', 'lay', 'layer',
         'lead', 'leader', 'league', 'leave', 'leg', 'length', 'lesson', 'let', 'letter', 'level',
         'lie', 'life', 'lift', 'light', 'limit', 'line', 'link', 'lip', 'list', 'listen',
         'living', 'load', 'loan', 'local', 'lock', 'log', 'long', 'look', 'loss', 'love',
         'low', 'luck', 'lunch', 'mail', 'main', 'major', 'make', 'male', 'mall', 'man',
         'manner', 'many', 'map', 'march', 'mark', 'market', 'master', 'match', 'mate', 'math',
         'matter', 'maybe', 'meal', 'meat', 'media', 'medium', 'meet', 'member', 'memory', 'menu',
         'mess', 'metal', 'method', 'middle', 'might', 'milk', 'mind', 'mine', 'minor', 'minute',
         'mirror', 'miss', 'mix', 'mobile', 'mode', 'model', 'mom', 'moment', 'money', 'month',
         'mood', 'most', 'mother', 'motor', 'mouse', 'mouth', 'move', 'movie', 'mud', 'muscle',
         'music', 'nail', 'name', 'nasty', 'nation', 'native', 'nature', 'neat', 'neck', 'nerve',
         'net', 'news', 'night', 'nobody', 'noise', 'normal', 'north', 'nose', 'note', 'notice',
         'novel', 'number', 'nurse', 'object', 'offer', 'office', 'oil', 'one', 'option', 'orange',
         'order', 'other', 'oven', 'owner', 'pace', 'pack', 'page', 'pain', 'paint', 'pair',
         'panic', 'paper', 'parent', 'park', 'part', 'party', 'pass', 'past', 'path', 'pause',
         'pay', 'peace', 'peak', 'pen', 'people', 'period', 'permit', 'person', 'phase', 'phone',
         'photo', 'phrase', 'piano', 'pick', 'pie', 'piece', 'pin', 'pipe', 'pitch', 'pizza',
         'place', 'plan', 'plane', 'plant', 'plate', 'play', 'player', 'plenty', 'poem', 'poet',
         'poetry', 'point', 'police', 'policy', 'pool', 'pop', 'post', 'pot', 'potato', 'pound',
         'power', 'press', 'price', 'pride', 'priest', 'print', 'prior', 'prize', 'profit', 'prompt',
         'proof', 'public', 'pull', 'punch', 'purple', 'push', 'put', 'queen', 'quiet', 'quit',
         'quote', 'race', 'radio', 'rain', 'raise', 'range', 'rate', 'ratio', 'raw', 'reach',
         'read', 'reason', 'recipe', 'record', 'red', 'refuse', 'region', 'regret', 'relief', 'remote',
         'remove', 'rent', 'repair', 'repeat', 'reply', 'report', 'resist', 'resort', 'rest', 'result',
         'return', 'reveal', 'review', 'reward', 'rice', 'rich', 'ride', 'ring', 'rip', 'rise',
         'risk', 'river', 'road', 'rock', 'role', 'roll', 'roof', 'room', 'rope', 'rough',
         'round', 'row', 'royal', 'rub', 'ruin', 'rule', 'run', 'rush', 'sad', 'safe',
         'safety', 'sail', 'salad', 'salary', 'sale', 'salt', 'sample', 'sand', 'save', 'scale',
         'scene', 'scheme', 'school', 'score', 'screen', 'screw', 'script', 'sea', 'search', 'season',
         'seat', 'second', 'secret', 'sector', 'self', 'sell', 'senior', 'sense', 'series', 'serve',
         'set', 'sex', 'shake', 'shame', 'shape', 'share', 'she', 'shift', 'shine', 'ship',
         'shirt', 'shock', 'shoe', 'shoot', 'shop', 'shot', 'show', 'shower', 'sick', 'side',
         'sign', 'signal', 'silly', 'silver', 'simple', 'sing', 'singer', 'single', 'sink', 'sir',
         'sister', 'site', 'size', 'skill', 'skin', 'skirt', 'sky', 'sleep', 'slice', 'slide',
         'slip', 'smell', 'smile', 'smoke', 'snow', 'sock', 'soft', 'soil', 'solid', 'son',
         'song', 'sort', 'sound', 'soup', 'source', 'south', 'space', 'spare', 'speech', 'speed',
         'spell', 'spend', 'spirit', 'spite', 'split', 'sport', 'spot', 'spray', 'spread', 'spring',
         'square', 'stable', 'staff', 'stage', 'stand', 'star', 'start', 'state', 'status', 'stay',
         'steak', 'steal', 'step', 'stick', 'still', 'stock', 'stop', 'store', 'storm', 'story',
         'strain', 'street', 'stress', 'strike', 'string', 'strip', 'stroke', 'studio', 'study', 'stuff',
         'stupid', 'style', 'suck', 'sugar', 'suit', 'summer', 'sun', 'survey', 'sweet', 'swim',
         'swing', 'switch', 'system', 'table', 'tackle', 'tale', 'talk', 'tank', 'tap', 'target',
         'task', 'taste', 'tax', 'tea', 'teach', 'team', 'tear', 'tell', 'tennis', 'term',
         'test', 'text', 'thanks', 'theme', 'theory', 'thing', 'throat', 'ticket', 'tie', 'till',
         'time', 'tip', 'title', 'today', 'toe', 'tone', 'tongue', 'tool', 'tooth', 'top',
         'topic', 'total', 'touch', 'tough', 'tour', 'towel', 'tower', 'town', 'track', 'trade',
         'train', 'trash', 'travel', 'treat', 'tree', 'trick', 'trip', 'truck', 'trust', 'truth',
         'try', 'tune', 'turn', 'twist', 'two', 'type', 'uncle', 'union', 'unique', 'unit',
         'upper', 'use', 'user', 'usual', 'value', 'vast', 'video', 'view', 'virus', 'visit',
         'visual', 'voice', 'volume', 'wait', 'wake', 'walk', 'wall', 'war', 'wash', 'watch',
         'water', 'wave', 'way', 'wealth', 'wear', 'web', 'week', 'weight', 'weird', 'west',
         'wheel', 'while', 'white', 'whole', 'wife', 'will', 'win', 'wind', 'window', 'wine',
         'wing', 'winner', 'winter', 'wish', 'woman', 'wonder', 'wood', 'word', 'work', 'worker',
         'world', 'worry', 'worth', 'wrap', 'writer', 'yard', 'year', 'yellow', 'you', 'young',
         'youth', 'zone']