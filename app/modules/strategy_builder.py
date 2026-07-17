import operator

class StrategyEvaluator:
    """
    Evaluates no-code trading strategies based on a set of conditions.
    """
    def __init__(self):
        self.operations = {
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne
        }

    def evaluate_condition(self, left_value, operator_str, right_value):
        """
        Evaluates a single condition.
        """
        if operator_str not in self.operations:
            raise ValueError(f"Unsupported operator: {operator_str}")
        return self.operations[operator_str](left_value, right_value)

    def evaluate_rule_group(self, group, market_data):
        """
        Evaluates a group of rules with AND/OR logic.
        group: dict containing 'logic' (AND/OR) and 'rules' (list of rules or subgroups)
        """
        if not group or 'rules' not in group:
            return False

        logic = group.get('logic', 'AND').upper()
        results = []

        for rule in group['rules']:
            if 'rules' in rule: # It's a subgroup
                results.append(self.evaluate_rule_group(rule, market_data))
            else:
                # It's a simple rule: {'indicator': 'RSI', 'operator': '>', 'value': 70}
                indicator = rule.get('indicator')
                operator_str = rule.get('operator')
                value = rule.get('value')
                
                # Mock fetching actual indicator value from market_data
                current_val = market_data.get(indicator, 0)
                
                res = self.evaluate_condition(current_val, operator_str, value)
                results.append(res)
                
        if not results:
            return False
            
        if logic == 'AND':
            return all(results)
        elif logic == 'OR':
            return any(results)
        return False

    def evaluate_strategy(self, strategy, market_data):
        """
        Evaluates full strategy with entry and exit conditions.
        """
        entry_result = False
        exit_result = False
        
        if 'entry_rules' in strategy:
             entry_result = self.evaluate_rule_group(strategy['entry_rules'], market_data)
             
        if 'exit_rules' in strategy:
             exit_result = self.evaluate_rule_group(strategy['exit_rules'], market_data)
             
        return {
            'should_enter': entry_result,
            'should_exit': exit_result
        }
