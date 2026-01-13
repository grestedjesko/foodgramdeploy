import styles from './styles.module.css'
import { Icons } from '..'

const RecipePopup = ({
  recipe,
  onClose
}) => {
  if (!recipe) return null;

  return (
    <div className={styles.popup} onClick={e => {
      if (e.target === e.currentTarget) {
        onClose && onClose()
      }
    }}>
      <div className={styles.popup__content}>
        <div className={styles.popup__close} onClick={onClose}>
          <Icons.PopupClose />
        </div>
        
        <div className={styles.popup__header}>
          {recipe.image && (
            <img 
              src={recipe.image} 
              alt={recipe.name}
              className={styles.popup__image}
            />
          )}
          <div className={styles.popup__title_wrapper}>
            <h2 className={styles.popup__title}>{recipe.name}</h2>
            {recipe.category && (
              <p className={styles.popup__meta}>
                <span className={styles.popup__badge}>{recipe.category}</span>
                {recipe.area && <span className={styles.popup__badge}>{recipe.area}</span>}
              </p>
            )}
          </div>
        </div>

        <div className={styles.popup__body}>
          {recipe.ingredients && recipe.ingredients.length > 0 && (
            <div className={styles.popup__section}>
              <h3 className={styles.popup__section_title}>Ингредиенты:</h3>
              <ul className={styles.popup__ingredients}>
                {recipe.ingredients.map((ing, idx) => (
                  <li key={idx} className={styles.popup__ingredient}>
                    {ing.name} {ing.measure && `- ${ing.measure}`}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recipe.instructions && (
            <div className={styles.popup__section}>
              <h3 className={styles.popup__section_title}>Инструкция:</h3>
              <p className={styles.popup__instructions}>
                {recipe.instructions}
              </p>
            </div>
          )}

          {recipe.youtube && (
            <div className={styles.popup__section}>
              <a 
                href={recipe.youtube} 
                target="_blank" 
                rel="noopener noreferrer"
                className={styles.popup__link}
              >
                📺 Посмотреть видео на YouTube
              </a>
            </div>
          )}

          <div className={styles.popup__footer}>
            <p className={styles.popup__source}>
              Источник: {recipe.source || 'TheMealDB'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RecipePopup
