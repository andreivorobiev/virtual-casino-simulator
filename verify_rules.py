# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
"""Rule-level validation for Virtual Casino Simulator v9.
# Execute this statement as part of the module's documented control flow.
Run: python verify_rules.py
"""
# Import required dependency so this module can use its public functions or constants.
from casino.games.roulette import rules as rr, engine as re
# Import required dependency so this module can use its public functions or constants.
from casino.games.slots import engine as se
# Import required dependency so this module can use its public functions or constants.
from casino.games.blackjack import engine as bj
# Import required dependency so this module can use its public functions or constants.
from casino.games.baccarat import engine as bac
# Import required dependency so this module can use its public functions or constants.
from casino.games.keno import engine as ke
# Import required dependency so this module can use its public functions or constants.
from casino.games.bingo import engine as bi

# Set RESULTS to the value needed for the next operation.
RESULTS=[]
# Define the check function used by this module.
def check(req, cond, msg=''):
    # Branch when the following condition is true.
    if not cond: raise AssertionError(f'{req} failed: {msg}')
    # Execute this statement as part of the module's documented control flow.
    RESULTS.append({'requirement_id': req, 'status':'PASS', 'message':msg})

# Define the roulette_tests function used by this module.
def roulette_tests():
    # Set cat to the value needed for the next operation.
    cat=rr.catalog('double')
    # Define the has function used by this module.
    def has(t, nums): return any(b['type']==t and set(b['covered_numbers'])==set(nums) for b in cat)
    # Set check('ROU-001', rr.roulette_numbers('single') to the value needed for the next operation.
    check('ROU-001', rr.roulette_numbers('single') == ['0']+[str(i) for i in range(1,37)])
    # Set check('ROU-002', rr.roulette_numbers('double') to the value needed for the next operation.
    check('ROU-002', rr.roulette_numbers('double') == ['0','00']+[str(i) for i in range(1,37)])
    # Execute this statement as part of the module's documented control flow.
    check('ROU-010', has('straight',['17']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-011', has('split',['17','20']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-012', has('street',['16','17','18']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-013', has('corner',['17','18','20','21']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-014', has('line',['16','17','18','19','20','21']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-015', has('zero_split',['0','00']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-016', has('trio',['0','1','2']) or has('trio',['0','00','2']))
    # Execute this statement as part of the module's documented control flow.
    check('ROU-017', has('top_line',['0','00','1','2','3']))
    # Set b to the value needed for the next operation.
    b=rr.find_bet('double','split',['17','20']); res=re.settle_bet({'amount':5,'covered_numbers':['17','20'],'net_payout':17,'type':'split'},'17')
    # Set check('ROU-030', res['credit'] to the value needed for the next operation.
    check('ROU-030', res['credit']==90)
    # Set res2 to the value needed for the next operation.
    res2=re.settle_bet({'amount':10,'covered_numbers':list(rr.RED_NUMBERS),'net_payout':1,'type':'red'},'0','la_partage')
    # Set check('ROU-031', res2['credit'] to the value needed for the next operation.
    check('ROU-031', res2['credit']==5)
    # Set res3 to the value needed for the next operation.
    res3=re.settle_bet({'amount':10,'covered_numbers':list(rr.RED_NUMBERS),'net_payout':1,'type':'red'},'0','en_prison')
    # Execute this statement as part of the module's documented control flow.
    check('ROU-032', res3['carry'] is True)

# Define the slots_tests function used by this module.
def slots_tests():
    # Set st to the value needed for the next operation.
    st=se.default_state(); spin=se.spin(st,5,1)
    # Set check('SLOT-001', len(spin['grid']) to the value needed for the next operation.
    check('SLOT-001', len(spin['grid'])==3 and len(spin['grid'][0])==5)
    # Set check('SLOT-002', spin['active_lines'] to the value needed for the next operation.
    check('SLOT-002', spin['active_lines']==5 and spin['cost']==5)
    # Set check('SLOT-003', set(se.PAYLINES.keys()) to the value needed for the next operation.
    check('SLOT-003', set(se.PAYLINES.keys())=={1,3,5,9,20})
    # Execute this statement as part of the module's documented control flow.
    check('SLOT-004', 'WILD' in se.SYMBOLS and 'SCATTER' in se.SYMBOLS)

# Define the blackjack_tests function used by this module.
def blackjack_tests():
    # Set check('BJ-001', bj.hand_total(['A♠','6♥'])['soft'] and bj.ha to the value needed for the next operation.
    check('BJ-001', bj.hand_total(['A♠','6♥'])['soft'] and bj.hand_total(['A♠','6♥'])['total']==17)
    # Set check('BJ-002', bj.hand_total(['A♠','A♥','5♦'])['soft'] and  to the value needed for the next operation.
    check('BJ-002', bj.hand_total(['A♠','A♥','5♦'])['soft'] and bj.hand_total(['A♠','A♥','5♦'])['total']==17)
    # Set st to the value needed for the next operation.
    st=bj.default_state(); st['shoe']=['9♠']*200; rnd=bj.new_round(st,'human',10); check('BJ-003', rnd['status'] in ('player_turn','settled_pending_credit'))
    # Set st2 to the value needed for the next operation.
    st2=bj.default_state(); h={'cards':['8♠','8♥'],'actions':['split'],'is_split_hand':True}; check('BJ-004', bj.can_double(st2,h) is True)
    # Set st2['rules']['double_after_split'] to the value needed for the next operation.
    st2['rules']['double_after_split']=False; check('BJ-005', bj.can_double(st2,h) is False)

# Define the baccarat_tests function used by this module.
def baccarat_tests():
    # Set st to the value needed for the next operation.
    st=bac.default_state(); st['shoe']=['9♠']*200; st['open_bets']=[{'bet_id':'b','player_id':'human','type':'player','amount':1,'label':'Player'}]
    # Set coup to the value needed for the next operation.
    coup=bac.deal_coup(st); check('BAC-001', 'player_cards' in coup and 'banker_cards' in coup)
    # Set check('BAC-002', len(coup['player_cards'])> to the value needed for the next operation.
    check('BAC-002', len(coup['player_cards'])>=2 and len(coup['banker_cards'])>=2)
    # Set check('BAC-003', bac.value('K♠') to the value needed for the next operation.
    check('BAC-003', bac.value('K♠')==0 and bac.value('A♣')==1)
    # Set check('BAC-004', bac.total(['9♠','8♣']) to the value needed for the next operation.
    check('BAC-004', bac.total(['9♠','8♣'])==7)

# Define the keno_tests function used by this module.
def keno_tests():
    # Set check('KENO-001', set(ke.PAYTABLE.keys()) to the value needed for the next operation.
    check('KENO-001', set(ke.PAYTABLE.keys())==set(range(1,21)))
    # Set st to the value needed for the next operation.
    st=ke.default_state(); t=ke.add_ticket(st,'human',[1,2,3],5); d=ke.draw(st); check('KENO-002', len(d['drawn'])==20 and not st['open_tickets'])

# Define the bingo_tests function used by this module.
def bingo_tests():
    # Set card to the value needed for the next operation.
    card=bi.make_card(); check('BINGO-001', card['N'][2]=='FREE')
    # Set check('BINGO-002', all(1< to the value needed for the next operation.
    check('BINGO-002', all(1<=x<=15 for x in card['B']))
    # Set st to the value needed for the next operation.
    st=bi.default_state(); sess=bi.start_session(st,'human',5,'line',bot_players=[{'player_id':'bot_1','amount':5}]); check('BINGO-003', len(sess['cards'])==2)
    # Set check('BINGO-004', bi.ball_label(1) to the value needed for the next operation.
    check('BINGO-004', bi.ball_label(1)=='B-1' and bi.ball_label(75)=='O-75')

# Define the main function used by this module.
def main():
    # Iterate through the collection to process each item.
    for fn in [roulette_tests, slots_tests, blackjack_tests, baccarat_tests, keno_tests, bingo_tests]: fn()
    # Write diagnostic output so the current operation can be inspected.
    print(f'[ok] {len(RESULTS)} rule checks passed')
    # Iterate through the collection to process each item.
    for r in RESULTS: print(f"  {r['requirement_id']} PASS")
# Branch when the following condition is true.
if __name__=='__main__': main()
