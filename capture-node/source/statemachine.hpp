// Copyright (C) 2017 Electronic Arts Inc.  All rights reserved.

#pragma once

template <typename stateT>
class StateMachine
{
public:
	StateMachine(stateT initialState) : m_state(initialState) { }
	virtual ~StateMachine() {}
	void GotoState(stateT state) {
		stateT oldState = m_state;
		m_state = state;
		ChangeState(oldState, m_state);
	}
	stateT CurrentState() { return m_state; }
protected:
	// Executre transition code, then return a new state if we need to change again, or STATE_UNCHANGED.
	virtual void ChangeState(stateT fromState, stateT toState) = 0;
private:
	stateT m_state;
};
