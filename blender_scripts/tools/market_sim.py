#import imp
from random import random, randrange, choice, gauss, uniform
from copy import copy

#import pickle


PRICE_ADJUST_MODE = 'chance'
PRICE_ADJUST_CHANCE = 0.9
PRICE_ADJUST_MEAN = 1
PRICE_ADJUST_DEV = 0.1
PRICE_CONCESSION = PRICE_ADJUST_MEAN
MAX_PRICE = 30

class Agent(object):
    """docstring for Agent."""
    def __init__(
        self,
        type = 'buyer',
        interaction_mode = None,
        price_limit = None,
        initial_price = None, #For setting market expectations
    ):
        super().__init__()
        self.type = type
        if interaction_mode == None:
            raise Warning('Agent needs interaction_mode')
        self.interaction_mode = interaction_mode

        if price_limit == None:
            raise Warning('Everyone has a price!')
        self.price_limit = price_limit

        #determine initial goal price
        if initial_price == None:
            initial_price = self.price_limit
        else:
            if self.type == 'buyer':
                initial_price = min(initial_price, self.price_limit)
            elif self.type == 'seller':
                initial_price = max(initial_price, self.price_limit)

        self.goal_prices = [initial_price] #initial value

    def adjust_price(self, success = None, set_price = None):
        if set_price != None:
            self.goal_prices.append(set_price)
        else:
            if success == None:
                raise Warning('Need to know outcome to adjust price')
            if PRICE_ADJUST_MODE == 'gauss':
                #1, with just a touch of variability to avoid weird states
                adjust_amount = gauss(PRICE_ADJUST_MEAN, PRICE_ADJUST_DEV)
            if PRICE_ADJUST_MODE == 'chance':
                if random() < PRICE_ADJUST_CHANCE:
                    adjust_amount = PRICE_ADJUST_MEAN
                else:
                    adjust_amount = 0
            if success == True:
                if self.type == 'buyer': #and self.interaction_mode != 'seller_asks_buyer_decides':
                    self.goal_prices.append(self.goal_prices[-1] - adjust_amount)
                if self.type == 'seller':
                    self.goal_prices.append(self.goal_prices[-1] + adjust_amount)
            if success == False:
                if self.type == 'buyer': #and self.interaction_mode != 'seller_asks_buyer_decides':
                    self.goal_prices.append(min(self.goal_prices[-1] + adjust_amount, self.price_limit))
                if self.type == 'seller':
                    self.goal_prices.append(max(self.goal_prices[-1] - adjust_amount, self.price_limit))

class Meeting(object):
    """docstring for Meeting."""
    def __init__(self,
        buyer = None,
        seller = None,
        interaction_mode = None,
        concession_size = 0
    ):
        super().__init__()
        self.buyer = buyer
        self.seller = seller

        if self.seller == None or self.buyer == None:
            raise Warning('Meeting is missing a buyer or a seller')



        bid = min(self.buyer.goal_prices[-1] + concession_size, self.buyer.price_limit)
        ask = max(self.seller.goal_prices[-1] - concession_size, self.seller.price_limit)

        if interaction_mode == None:
            raise Warning('Buyers and sellers have undefined interaction mode')

        self.transaction_price = None

        if interaction_mode == 'seller_asks_buyer_decides':
            if ask <= bid:
                self.transaction_price = ask
        elif interaction_mode == 'buyer_gets_it': #End of day desperate to sell
            self.transaction_price = bid
        else:
            if ask <= bid:
                self.transaction_price = uniform(ask, bid + 1)

            else:
                if interaction_mode == 'negotiate':
                    minimum = max(bid, seller.price_limit)
                    maximum = min(ask, buyer.price_limit)
                    if minimum <= maximum:
                        self.transaction_price = uniform(minimum, maximum + 1)
                elif interaction_mode == 'walk': #Not necessary, but here for clarity
                    self.transaction_price = None
                elif interaction_mode == 'mix_negotiate_and_walk':
                    if random() < 0.5: #Just 50-50 willingness for now, regardless of spread
                        minimum = max(bid, seller.price_limit)
                        maximum = min(ask, buyer.price_limit)
                        if minimum <= maximum:
                            self.transaction_price = uniform(minimum, maximum + 1)
                else:
                    raise Warning('Interaction mode not implemented')

class Session(object):
    """docstring for Session."""
    def __init__(
        self,
        buyers = None,
        sellers = None,
        interaction_mode = None,
        session_mode = None,
        trim_participants = False,
        #meetings = []
    ):
        super().__init__()
        self.buyers = buyers
        self.sellers = sellers
        self.num_sellers = len(self.sellers)
        self.interaction_mode = interaction_mode
        #self.meetings = meetings
        if session_mode == None:
            raise Warning('Session needs mode')
        self.session_mode = session_mode
        self.trim_participants = trim_participants

        self.rounds = []

        self.conduct_session()
        self.get_stats()

    def conduct_session(self):
        if self.session_mode == 'one_shot':
            round = []
            for i in range(min( len(self.buyers), len(self.sellers) )):
                buyer = choice(self.buyers)
                self.buyers.remove(buyer)
                seller = choice(self.sellers)
                self.sellers.remove(seller)

                round.append(
                    Meeting(
                        buyer = buyer,
                        seller = seller,
                        interaction_mode = self.interaction_mode
                    )
                )

                #Adjust prices after meeting
                last_price = round[-1].transaction_price
                success = True
                if last_price == None: #Fail
                    success = False

                #In one special case, set the new buyer price exactly
                if success == True and \
                    self.interaction_mode == 'seller_asks_buyer_decides':
                    buyer.adjust_price(set_price = last_price)
                else:
                    buyer.adjust_price(success = success)
                seller.adjust_price(success = success)


            self.rounds.append(round)

            #The number of sellers fluctuates, so sometimes buyers don't get matched
            #and need their expectation upated for the next day
            for buyer in self.buyers:
                buyer.goal_prices.append(buyer.goal_prices[-1])

        if self.session_mode == 'rounds' or self.session_mode == 'rounds_w_concessions':
            disqualified = []
            sellers_this_round = copy(self.sellers)
            buyers_this_round = copy(self.buyers)

            round_count = 0
            while len(buyers_this_round) > 0 and len(sellers_this_round) > 0:
                round_count += 1
                round = []
                print(' Round ' + str(round_count))

                max_buyer_price = max([x.goal_prices[-1] for x in buyers_this_round])
                min_seller_price = min([x.goal_prices[-1] for x in sellers_this_round])
                if self.trim_participants == True:
                    #Filter out impossible-to-please agents
                    print('  Max price: ' + str(max_buyer_price))
                    disqualified += [x for x in sellers_this_round if x.goal_prices[-1] > max_buyer_price]
                    sellers_this_round = [x for x in sellers_this_round if x.goal_prices[-1] <= max_buyer_price]
                    print('  ' + str(len(sellers_this_round)) + ' sellers')

                    print('  Min price: ' + str(min_seller_price))
                    disqualified += [x for x in buyers_this_round if x.goal_prices[-1] < min_seller_price]
                    buyers_this_round = [x for x in buyers_this_round if x.goal_prices[-1] >= min_seller_price]
                    print('  ' + str(len(buyers_this_round)) + ' buyers')
                elif max_buyer_price < min_seller_price:
                    break

                #Prep container for creatures who will go to next round
                buyers_next_round = []
                sellers_next_round = []

                #Create pairs
                for i in range(min(len(buyers_this_round), len(sellers_this_round))):
                    pair_has_been_tried = True
                    while pair_has_been_tried == True:
                        pair_has_been_tried = False
                        buyer = choice(buyers_this_round)
                        seller = choice(sellers_this_round)

                        for meeting in round:
                            if meeting.buyer == buyer and meeting.seller == seller:
                                pair_has_been_tried = True
                                print('Oop, need to try another pair')

                        if pair_has_been_tried == False:
                            buyers_this_round.remove(buyer)
                            sellers_this_round.remove(seller)

                    round.append(
                        Meeting(
                            buyer = buyer,
                            seller = seller,
                            interaction_mode = self.interaction_mode
                        )
                    )

                    last_price = round[-1].transaction_price

                    if last_price == None:
                        sellers_next_round.append(seller)
                        buyers_next_round.append(buyer)
                    else: #success!
                        if self.interaction_mode == 'seller_asks_buyer_decides':
                            buyer.adjust_price(set_price = last_price)
                        else:
                            buyer.adjust_price(success = True)
                        seller.adjust_price(success = True)


                #Put any extras in next round
                for buyer in buyers_this_round:
                    buyers_next_round.append(buyer)
                for seller in sellers_this_round:
                    sellers_next_round.append(seller)

                #Reset for next loop
                buyers_this_round = buyers_next_round
                sellers_this_round = sellers_next_round

                self.rounds.append(round)

            #Put leftovers in disqualified. Will sometimes make an agen adjust
            #price even when they never got a chance, but that will be fairly rare.
            #Main point is to make sure agents who have failed do end up
            #adjusting price
            for buyer in buyers_this_round:
                disqualified.append(buyer)
            for seller in sellers_this_round:
                disqualified.append(seller)

            if self.session_mode == 'rounds':
                #Agents who never made a deal adjust prices
                for agent in disqualified:
                    agent.adjust_price(success = False)
            else:
                #Try again, making a concession on price and using the final
                #price for the adjustment. Purpose of this is to get transaction
                #count up.
                buyers_this_round = [x for x in disqualified if x.type == 'buyer']
                disqualified = [x for x in disqualified if x not in buyers_this_round]
                sellers_this_round = [x for x in disqualified if x.type == 'seller']
                disqualified = [x for x in disqualified if x not in sellers_this_round]

                #Similar to loop from before, but always negotiate to see if a
                #deal is possible within base limits
                while len(buyers_this_round) > 0 and len(sellers_this_round) > 0:
                    round_count += 1
                    round = []
                    print(' Retry round ' + str(round_count))
                    max_buyer_price = max(
                        [
                            min(x.goal_prices[-1] + PRICE_CONCESSION, x.price_limit) \
                            for x in buyers_this_round
                        ]
                    )
                    min_seller_price = min(
                        [
                            max(x.goal_prices[-1] - PRICE_CONCESSION, x.price_limit) \
                            for x in sellers_this_round
                        ]
                    )

                    if self.trim_participants == True:
                        #Filter out impossible-to-please agents
                        #print('  Max price: ' + str(max_buyer_price))
                        disqualified += [x for x in sellers_this_round if \
                                        max(x.goal_prices[-1] - PRICE_CONCESSION, x.price_limit) > max_buyer_price]
                        sellers_this_round = [x for x in sellers_this_round if \
                                        max(x.goal_prices[-1] - PRICE_CONCESSION, x.price_limit) <= max_buyer_price]
                        #print('  ' + str(len(sellers_this_round)) + ' sellers')

                        #print('  Min price: ' + str(min_seller_price))
                        disqualified += [x for x in buyers_this_round if \
                                        min(x.goal_prices[-1] + PRICE_CONCESSION, x.price_limit) < min_seller_price]
                        buyers_this_round = [x for x in buyers_this_round if \
                                        min(x.goal_prices[-1] + PRICE_CONCESSION, x.price_limit) >= min_seller_price]
                        #print('  ' + str(len(buyers_this_round)) + ' buyers')
                    elif max_buyer_price < min_seller_price:
                        break

                    #Prep container for creatures who will go to next round
                    buyers_next_round = []
                    sellers_next_round = []

                    #Create pairs
                    for i in range(min(len(buyers_this_round), len(sellers_this_round))):
                        pair_has_been_tried = True
                        while pair_has_been_tried == True:
                            pair_has_been_tried = False
                            buyer = choice(buyers_this_round)
                            seller = choice(sellers_this_round)

                            for meeting in round:
                                if meeting.buyer == buyer and meeting.seller == seller:
                                    pair_has_been_tried = True
                                    print('Oop, need to try another pair, extras')

                            if pair_has_been_tried == False:
                                buyers_this_round.remove(buyer)
                                sellers_this_round.remove(seller)

                        round.append(
                            Meeting(
                                buyer = buyer,
                                seller = seller,
                                interaction_mode = self.interaction_mode,
                                concession_size = PRICE_CONCESSION
                            )
                        )

                        last_price = round[-1].transaction_price

                        if last_price == None:
                            buyers_next_round.append(buyer)
                            sellers_next_round.append(seller)
                        else: #success!
                            buyer.adjust_price(set_price = last_price)
                            seller.adjust_price(set_price = last_price)

                    #Put any extras in next round
                    for buyer in buyers_this_round:
                        buyers_next_round.append(buyer)
                    for seller in sellers_this_round:
                        sellers_next_round.append(seller)

                    #Reset for next loop
                    buyers_this_round = buyers_next_round
                    sellers_this_round = sellers_next_round

                    self.rounds.append(round)

                #Put leftovers in disqualified. Will sometimes make an agen adjust
                #price even when they never got a chance, but that will be fairly rare.
                #Main point is to make sure agents who have failed do end up
                #adjusting price
                for buyer in buyers_this_round:
                    disqualified.append(buyer)
                for seller in sellers_this_round:
                    disqualified.append(seller)

                for agent in disqualified:
                    agent.adjust_price(success = False)




    def get_stats(self):
        total_price = 0
        self.num_transactions = 0
        self.failed_meetings = 0
        for round in self.rounds:
            for meet in round:
                if meet.transaction_price != None:
                    #print(meet.transaction_price)
                    total_price += meet.transaction_price
                    self.num_transactions += 1
                else:
                    self.failed_meetings += 1
        if self.num_transactions > 0:
            self.avg_price = total_price / self.num_transactions
        else:
            self.avg_price = None

class Market(object):
    """docstring for Market."""
    def __init__(
        self,
        initial_agents = None,
        num_initial_buyers = 0,
        num_initial_sellers = 0,
        price_range = [0, MAX_PRICE],
        initial_price = None,
        interaction_mode = 'negotiate',
        session_mode = 'rounds',
        fluid_sellers = True
    ):
        super().__init__()
        self.price_range = price_range
        self.initial_price = initial_price

        #Interaction modes
        #Seller price set, buyer accept or deny
        #Always walk away
        #Always negotiate
        #Mix walk away and negotiation
        self.interaction_mode = interaction_mode
        self.session_mode = session_mode

        self.agents_lists = []
        if initial_agents == None:
            self.generate_agents(
                num_sellers = num_initial_sellers,
                num_buyers = num_initial_buyers
            )
        else:
            self.agents_lists.append(initial_agents)

        self.sessions = []
        self.fluid_sellers = fluid_sellers

    def get_point_on_supply_curve(self, shape = 'linear'):
        if shape == 'linear':
            return randrange(self.price_range[0], self.price_range[1] + 1)
        if shape == 'quadratic':
            x = randrange(self.price_range[0], self.price_range[1] + 1)
            #return math.floor(x ** 2 / (2 * self.price_range[1]) + x / 2)
            return math.floor(x ** 2 / (self.price_range[1]))
            #return math.floor(x ** 3 / self.price_range[1] ** 2)
            pass

    def get_point_on_demand_curve(self, shape = 'linear'):
        if shape == 'linear':
            return randrange(self.price_range[0], self.price_range[1] + 1)
        if shape == 'quadratic': #Same as supply, taking advantage of symmetry
            x = randrange(self.price_range[0], self.price_range[1] + 1)
            #return math.floor(x ** 2 / (2 * self.price_range[1]) + x / 2)
            return math.floor(x ** 2 / (self.price_range[1]))
            #return math.floor(x ** 3 / self.price_range[1] ** 2)
            pass

    def generate_agents(self, num_buyers = None, num_sellers = None):
        new_agent_list = []
        for i in range(num_buyers):
            new_buyer = Agent(
                type = 'buyer',
                price_limit = self.get_point_on_demand_curve(shape = 'linear'),
                initial_price = self.initial_price,
                interaction_mode = self.interaction_mode
            )
            new_agent_list.append(new_buyer)
        for i in range(num_sellers):
            new_seller = Agent(
                type = 'seller',
                price_limit = self.get_point_on_supply_curve(shape = 'linear'),
                initial_price = self.initial_price,
                interaction_mode = self.interaction_mode
            )
            new_agent_list.append(new_seller)

        self.agents_lists.append(new_agent_list)

    def new_session(self, session_mode = None):
        if session_mode == None:
            session_mode = self.session_mode

        #There is a new list of eligible agents for each session.
        #This might be predetermined before init of market sim, but if not,
        #tack on a copy of the previous list until there's one extra, which
        #will correspond to the session about to be constructed.
        #This is done so sellers can be drawn as non-participants, and their
        #numbers can be manually changed.
        while len(self.agents_lists) <= len(self.sessions):
            self.agents_lists.append(self.agents_lists[-1])

        buyers = []
        sellers = []

        if len(self.sessions) == 0:
            expected_price = self.initial_price
        else:
            expected_price = self.sessions[-1].avg_price

        #Sorts agents into buyers and sellers. Could be more generalized and
        #make all agents able to buy or sell. Not now, though.
        for agent in self.agents_lists[-1]:
            if agent.type == 'seller':
                if self.fluid_sellers == True and \
                    expected_price != None and \
                    expected_price < agent.price_limit:
                    #If seller sits session out, add to its goal_prices list
                    #to keep them the same length
                    agent.goal_prices.append(agent.price_limit)
                else:
                    sellers.append(agent)
            if agent.type == 'buyer':
                buyers.append(agent)

        self.sessions.append(
            Session(
                buyers = buyers,
                sellers = sellers,
                interaction_mode = self.interaction_mode,
                session_mode = session_mode,
                #meetings = []
                #For some reason, the default meetings value doesn't work,
                #It uses the meetings from the previous sim unless the
                #meetings kwarg is specified.
            )
        )
        '''for agent in self.agents:
            print(len(agent.goal_prices))'''