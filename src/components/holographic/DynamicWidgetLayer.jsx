import React, { useState } from 'react';
import PalantirMissionWidget from './widgets/PalantirMissionWidget';
import SignatureMissionWidget from './widgets/SignatureMissionWidget';
import MindTheaterPheromoneWidget from './widgets/MindTheaterPheromoneWidget';
import DreamFlowWidgets from './widgets/DreamFlowWidgets';
import IntentSurfaceWidget from './widgets/IntentSurfaceWidget';
import EmpathyDashboard from './widgets/EmpathyDashboard';
import KnowledgeGraphExplorer from './widgets/KnowledgeGraphExplorer';
import ReasoningChain from './widgets/ReasoningChain';

const SIGNATURE_TYPES = new Set([
    'mind_reel', 'pheromone_map', 'multiverse_desk', 'personal_graph', 'morphic_field',
    'system3', 'blackboard_theater', 'flow_guardian', 'dream_insight', 'world_graph', 'evolution_lab',
]);

const NEW_WIDGET_TYPES = new Set(['mind_reel', 'pheromone_map', 'dream_insight', 'flow_guardian', 'evolution_lab']);
const INTENT_SURFACE_TYPES = new Set([
    'cad_feature_timeline',
    'design_court',
    'simulation_variants',
    'certification_evidence',
    'tool_timeline',
    'dream_diff',
]);
const HUMAN_CONNECTION_TYPES = new Set(['empathy_dashboard', 'knowledge_graph', 'reasoning_chain']);

const MissionWidget = ({ widget, ...rest }) => {
    if (INTENT_SURFACE_TYPES.has(widget?.type)) {
        return <IntentSurfaceWidget widget={widget} {...rest} />;
    }
    if (HUMAN_CONNECTION_TYPES.has(widget?.type)) {
        if (widget.type === 'empathy_dashboard') {
            return <EmpathyDashboard socket={rest.socket} onDismiss={rest.onDismiss} />;
        }
        if (widget.type === 'knowledge_graph') {
            return <KnowledgeGraphExplorer socket={rest.socket} onDismiss={rest.onDismiss} />;
        }
        if (widget.type === 'reasoning_chain') {
            return <ReasoningChain socket={rest.socket} onDismiss={rest.onDismiss} />;
        }
    }
    if (NEW_WIDGET_TYPES.has(widget?.type)) {
        if (widget.type === 'mind_reel' || widget.type === 'pheromone_map') {
            return <MindTheaterPheromoneWidget widget={widget} {...rest} />;
        }
        if (['dream_insight', 'flow_guardian', 'evolution_lab'].includes(widget.type)) {
            return <DreamFlowWidgets widget={widget} {...rest} />;
        }
    }
    return SIGNATURE_TYPES.has(widget?.type)
        ? <SignatureMissionWidget widget={widget} {...rest} />
        : <PalantirMissionWidget widget={widget} {...rest} />;
};

const DynamicWidgetLayer = ({ widgets, onDismiss, socket }) => {
    const [heroId, setHeroId] = useState(null);
    const hero = widgets.find((w) => w.id === heroId);

    const toggleHero = (widget) => {
        setHeroId((current) => (current === widget.id ? null : widget.id));
    };

    const stack = widgets.filter((w) => w.id !== heroId);

    return (
        <>
            {hero && (
                <div className="ada-mission-hero-backdrop" onClick={() => setHeroId(null)} role="presentation">
                    <div className="ada-mission-hero-slot" onClick={(e) => e.stopPropagation()} role="presentation">
                        <MissionWidget
                            widget={hero}
                            socket={socket}
                            onDismiss={(id) => {
                                onDismiss(id);
                                setHeroId(null);
                            }}
                            isHero
                        />
                    </div>
                </div>
            )}

            <div className="ada-mission-stack" aria-label="ADA mission panels">
                {stack.map((widget) => {
                    // Animated entrance with staggered delay
                    const idx = stack.indexOf(widget);
                    const delay = idx * 0.08;
                    return (
                        <div
                            key={widget.id}
                            className="ada-mission-slot ada-dynamic-animate-materialize"
                            style={{
                                zIndex: 30 + (widget.priority || 0),
                                animationDelay: `${delay}s`,
                            }}
                        >
                            <MissionWidget
                                widget={widget}
                                socket={socket}
                                onDismiss={onDismiss}
                                onExpand={toggleHero}
                            />
                        </div>
                    );
                })}
            </div>
        </>
    );
};

export default DynamicWidgetLayer;
