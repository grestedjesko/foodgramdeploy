import { Card, Title, Pagination, CardList, Container, Main, CheckboxGroup, Button, RecipePopup  } from '../../components'
import styles from './styles.module.css'
import { useRecipes } from '../../utils/index.js'
import { useEffect, useState, useRef } from 'react'
import api from '../../api'
import MetaTags from 'react-meta-tags'

const HomePage = ({ updateOrders }) => {
  const {
    recipes,
    setRecipes,
    recipesCount,
    setRecipesCount,
    recipesPage,
    setRecipesPage,
    handleLike,
    handleAddToCart
  } = useRecipes()

  const [importedRecipe, setImportedRecipe] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [importError, setImportError] = useState(null)
  const pollingIntervalRef = useRef(null)

  const getRecipes = ({ page = 1 }) => {
    api
      .getRecipes({ page })
      .then(res => {
        const { results, count } = res
        setRecipes(results)
        setRecipesCount(count)
      })
  }

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }

  const pollTaskStatus = (taskId) => {
    api
      .getCeleryTaskStatus({ task_id: taskId })
      .then(response => {
        console.log('Task status:', response)
        
        if (response.ready) {
          // Задача завершена - остановить polling
          stopPolling()
          
          if (response.successful) {
            const result = response.result
            // Проверить, есть ли данные рецепта
            if (result.recipe) {
              setImportedRecipe(result.recipe)
            } else {
              setImportError('Рецепт не найден или произошла ошибка при импорте')
            }
          } else {
            setImportError(`Ошибка выполнения задачи: ${response.error || 'Неизвестная ошибка'}`)
          }
          
          setIsLoading(false)
        } else if (response.state === 'PROGRESS') {
          // Задача в процессе
          console.log('Progress:', response.progress)
        }
      })
      .catch(err => {
        console.error('Ошибка получения статуса:', err)
        stopPolling()
        setImportError('Не удалось получить статус задачи')
        setIsLoading(false)
      })
  }

  const handleImportRandomRecipe = () => {
    setIsLoading(true)
    setImportError(null)
    setImportedRecipe(null)
    
    // Остановить предыдущий polling, если есть
    stopPolling()
    
    api
      .getRandomMeal()
      .then(response => {
        console.log('Celery task created:', response)
        
        // Начать опрос статуса каждые 2 секунды
        pollingIntervalRef.current = setInterval(() => {
          pollTaskStatus(response.task_id)
        }, 2000)
        
        // Первый опрос сразу
        pollTaskStatus(response.task_id)
      })
      .catch(err => {
        console.error('Ошибка импорта:', err)
        setImportError('Не удалось создать задачу Celery. Попробуйте снова.')
        setIsLoading(false)
      })
  }

  const handleClosePopup = () => {
    setImportedRecipe(null)
    setImportError(null)
  }

  // Очистить интервал при размонтировании компонента
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [])

  useEffect(_ => {
    getRecipes({ page: recipesPage })
  }, [recipesPage])


  return <Main>
    <Container>
      <MetaTags>
        <title>Рецепты</title>
        <meta name="description" content="Фудграм - Рецепты" />
        <meta property="og:title" content="Рецепты" />
      </MetaTags>
      <div className={styles.title}>
        <Title title='Рецепты' />
        <Button
          modifier='style_dark-blue'
          clickHandler={handleImportRandomRecipe}
          disabled={isLoading}
        >
          {isLoading ? 'Импорт рецепта...' : '🎲 Случайный рецепт из TheMealDB'}
        </Button>
      </div>
      {importError && (
        <div className={styles.error}>
          {importError}
        </div>
      )}
      {recipes.length > 0 && <CardList>
        {recipes.map(card => <Card
          {...card}
          key={card.id}
          updateOrders={updateOrders}
          handleLike={handleLike}
          handleAddToCart={handleAddToCart}
        />)}
      </CardList>}
      <Pagination
        count={recipesCount}
        limit={6}
        page={recipesPage}
        onPageChange={page => setRecipesPage(page)}
      />
      {importedRecipe && (
        <RecipePopup
          recipe={importedRecipe}
          onClose={handleClosePopup}
        />
      )}
    </Container>
  </Main>
}

export default HomePage

